"""Custom Django management command to import a dataset CSV into the *cdb* database.

Usage:
    python manage.py import_ds DS1 /path/to/DS1.csv --map /path/to/column_map_DS1.csv

The mapping CSV drives how each CSV column is routed to tables/columns.
Columns in mapping file:
    source_column,target_table,target_column,extra_kwargs

*extra_kwargs* is optional JSON – e.g. {"property_group":"chemical"}

A minimal column_map_DS1.csv example is included at the end of this file
as a reference.
"""

import csv
import json
import re
from pathlib import Path
import decimal  # Required for Decimal handling
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import connections
from django.db.models import Q

from cdb_app import models as cdb


def get_or_create_material(class_code, subtype_code, specific_name=None, **extra):
    """
    Return an existing Material or create a new one based on the (class_code, subtype_code) identity.
    Creates the MaterialClass row first if it does not exist.
    Works on the 'cdb' database via Django's router.
    
    Extra parameters:
    - source_dataset: The dataset source (e.g., 'DS6')
    - notes: Notes to store with the material
    - reference_no: For linking with bibliographic references
    - study_no: For tracking study numbers
    """
    # 1. ensure the class exists
    cdb.MaterialClass.objects.using("cdb").get_or_create(
        class_code=class_code,
        defaults={"class_name": class_code.title()}
    )

    # 2. create or fetch the material
    # Set the material name that will be used both for lookup and display
    material_name = specific_name or subtype_code
    
    # Prepare defaults dictionary with all the extra parameters 
    defaults = {
        "specific_name": material_name,
    }
    
    # Add source_dataset if provided
    if "source_dataset" in extra:
        defaults["source_dataset"] = extra["source_dataset"]
        
    # Add notes if provided
    if "notes" in extra:
        defaults["notes"] = extra["notes"]
        
    # Try to find the material by class_code and subtype_code (primary identifiers)
    mat, created = cdb.Material.objects.using("cdb").get_or_create(
        material_class_id=class_code,  # Confirmed correct FK field name from error messages
        subtype_code=subtype_code,
        defaults=defaults
    )
    
    # If the material exists but doesn't have a specific_name, update it
    if not created and not mat.specific_name and material_name:
        mat.specific_name = material_name
        mat.save(using="cdb")
        
    return mat


def parse_specimen_info(specimen_info_str):
    """
    Parse specimen information from strings like '4x8 Cylinder' or '6x6x6 Cube'.
    Returns a tuple of (shape, dimensions_dict).
    Converts inches to mm if needed (1 inch = 25.4 mm).
    
    Examples:
    '4x8 Cylinder' -> ('Cylinder', {'diameter_mm': 101.6, 'length_mm': 203.2})
    '6x6x6 Cube' -> ('Cube', {'length_mm': 152.4, 'diameter_mm': 152.4})
    """
    if not specimen_info_str or not isinstance(specimen_info_str, str):
        return None, {}
        
    # Extract shape (case insensitive)
    shape = None
    if re.search(r'cylinder|cyl', specimen_info_str, re.IGNORECASE):
        shape = 'Cylinder'
    elif re.search(r'cube|cubic', specimen_info_str, re.IGNORECASE):
        shape = 'Cube'
    elif re.search(r'beam|prism', specimen_info_str, re.IGNORECASE):
        shape = 'Beam'
    else:
        # Default to cylinder if shape not specified but dimensions are present
        if re.search(r'\d+x\d+', specimen_info_str):
            shape = 'Cylinder'
        else:
            return None, {}  # Can't determine shape
    
    # Extract dimensions and convert to mm if needed
    # Look for patterns like 4x8, 6x6x6, 100x200, etc.
    dimensions = re.findall(r'\d+(?:\.\d+)?', specimen_info_str)
    dimensions = [float(d) for d in dimensions if d]
    
    # Check if dimensions are in inches (typically small values like 4x8)
    # or millimeters (typically larger values like 100x200)
    convert_to_mm = max(dimensions) < 30 if dimensions else False
    
    if convert_to_mm:
        # Convert inches to millimeters (1 inch = 25.4 mm)
        dimensions = [d * 25.4 for d in dimensions]
    
    result = {}
    if shape == 'Cylinder' and len(dimensions) >= 2:
        # For cylinders: first dimension is diameter, second is length
        result = {
            'nominal_diameter_mm': dimensions[0],
            'nominal_length_mm': dimensions[1]
        }
    elif shape == 'Cube' and len(dimensions) >= 1:
        # For cubes: all dimensions are the same, just need one
        result = {
            'nominal_diameter_mm': dimensions[0],  # Use diameter field for consistency
            'nominal_length_mm': dimensions[0]
        }
    elif shape == 'Beam' and len(dimensions) >= 3:
        # For beams: typically width×height×length
        result = {
            'nominal_diameter_mm': dimensions[0],  # Use diameter field for width
            'nominal_length_mm': dimensions[2]
        }
        
    return shape, result


class ColumnMap:
    """Abstraction to handle column mapping from source CSV to database tables."""
    def __init__(self, map_csv_path):
        # Read mapping from CSV
        self.rules = []
        
        with open(map_csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row['source_column'].strip():
                    continue
                    
                # Process the row
                row["extra_kwargs"] = json.loads(row.get("extra_kwargs") or "{}")
                
                # Extract binding parameters if they exist
                bind_params = {}
                for param in ['bind_to_reference', 'bind_to_study', 'bind_to_type', 'subtype_from_value']:
                    if param in row["extra_kwargs"]:
                        bind_params[param] = row["extra_kwargs"][param]
                        
                # Add binding parameters to the row separately for easier access
                row["bind_params"] = bind_params
                
                self.rules.append(row)

    def match(self, source_col):
        for r in self.rules:
            if r["source_column"].strip() == source_col.strip():
                return r
        return None


class Command(BaseCommand):
    help = "Import dataset CSV into cdb via mapping file"

    def add_arguments(self, parser):
        parser.add_argument('dataset_code', help='Dataset code (e.g. DS1)')
        parser.add_argument('csv_path', type=Path, help='Path to source CSV')
        parser.add_argument(
            '--map',
            dest='map_csv',
            type=Path,
            required=True,
            help='Path to column mapping CSV',
        )
        parser.add_argument(
            '--link-only',
            action='store_true',
            dest='link_only',
            help='Only link properties to existing materials in mixes, do not create new mixes',
        )

    @transaction.atomic(using="cdb")
    def handle(self, dataset_code, csv_path: Path, map_csv: Path, **opts):
        if not csv_path.exists():
            raise CommandError(f"Data file not found: {csv_path}")
        if not map_csv.exists():
            raise CommandError(f"Column map not found: {map_csv}")
            
        # Check if this is a link-only import which will only link properties to existing materials
        link_only = opts.get('link_only', False)
        if link_only:
            self.stdout.write("Running in link-only mode: will only link properties to existing materials")

        self.stdout.write("Ensuring material classes exist...")
        # Create required static entries
        for mat_class_code in ["CEMENT", "SCM", "AGGR_C", "AGGR_F", "WATER", "ADM", "FIBER"]:
            cdb.MaterialClass.objects.using("cdb").get_or_create(
                class_code=mat_class_code,
                defaults={"class_name": mat_class_code}
            )

        # Create test methods required for import
        self.stdout.write("Ensuring test methods exist...")
        # First, ensure we have a standard for the test methods
        standard, _ = cdb.Standard.objects.using("cdb").get_or_create(
            code="EN 12390-3",
            defaults={"title": "Testing hardened concrete - Part 3: Compressive strength of test specimens"}
        )
        
        # Now create test methods with IDs 1 and 2 if they don't exist
        test_methods = [
            (1, "Compressive strength - Cube", standard),
            (2, "Compressive strength - Cylinder", standard)
        ]
        
        for test_id, description, std in test_methods:
            _, created = cdb.TestMethod.objects.using("cdb").get_or_create(
                test_method_id=test_id,
                defaults={
                    "standard": std,
                    "description": description
                }
            )
            if created:
                self.stdout.write(f"Created TestMethod ID {test_id}: {description}")
                
        # Create unit for MPa if it doesn't exist
        _, created = cdb.UnitLookup.objects.using("cdb").get_or_create(
            unit_id=6,  # As referenced in the mapping
            defaults={
                "unit_symbol": "MPa",
                "description": "Megapascal"
            }
        )
        if created:
            self.stdout.write("Created Unit: MPa (ID: 6)")

        mapping = ColumnMap(map_csv)
        dataset, _ = cdb.Dataset.objects.using("cdb").get_or_create(
            dataset_name=dataset_code
        )

        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            row_num = 0
            for raw_row in reader:
                row_num += 1
                self._process_row(dataset, raw_row, mapping, row_num, link_only)

        self.stdout.write(self.style.SUCCESS("Import finished."))

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------

    def _process_row(self, dataset, raw_row, mapping: ColumnMap, row_num=0, link_only=False):
        """
        Process a single row of the dataset, applying the column mappings.
        """
        # Optionally save raw data in staging table for debugging/traceability
        try:
            cdb.StagingRaw.objects.using("cdb").create(
                dataset=dataset, row_json=raw_row
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Warning: Could not save to staging table: {e}"))

        # 1. Generate mix_code with proper dataset prefix
        # If Mix_ID exists in the raw data, use it; otherwise, generate one
        mix_code = raw_row.get("Mix_ID") or raw_row.get("mix_code") or ""
        
        # Ensure mix_code has proper dataset prefix
        dataset_prefix = f"{dataset.dataset_name}-"
        if not mix_code.strip():
            # Generate a unique mix code based on dataset name and row number
            mix_code = f"{dataset_prefix}{row_num}"
            self.stdout.write(f"Generated mix code: {mix_code}")
        elif not mix_code.startswith(dataset_prefix):
            # Add prefix if not already present
            mix_code = f"{dataset_prefix}{mix_code}"
            self.stdout.write(f"Standardized mix code: {mix_code}")
            
        # 2. Get or create ConcreteMix record
        try:
            # Normal mode - create mix if it doesn't exist
            mix_object, created = cdb.ConcreteMix.objects.using("cdb").get_or_create(
                mix_code=mix_code,
                defaults={
                    "dataset": dataset,
                    "notes": "",  # Will update with collected notes at end
                }
            )
            
            if created:
                self.stdout.write(f"Created new Mix: {mix_code}")
            else:
                self.stdout.write(f"Using existing Mix: {mix_code}")
                
            # For link-only mode, stop after creating the mix
            if link_only:
                return mix_object
            
            # 3. Collect notes (from rows marked as notes)
            notes_list = []

            # For created mixes, add dataset name to notes
            if created:
                notes_list.append(f"Dataset: {dataset.dataset_name}")

            # Append existing notes if any
            if mix_object.notes:
                notes_list.append(mix_object.notes)
                
            # 4. Initialize container for material references
            material_refs = {}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating/getting mix: {e}"))
            return

        # 4. Prepare containers for special processing
        biblio_ref_data = {}  # To collect bibliographic reference data
        component_calcs = {   # To collect data for component calculations
            'cement_kg_m3': None,
            'w_c_ratio': None,
            'cement_sand_ratio': None,
            'total_agg_cement_ratio': None,
            'rca_replacement_pct': None
        }
        aggregate_details = {  # To collect aggregate properties for later creation
            'RCA': {},
            'NCA': {},
            'NFA': {}
        }
        material_objects = {}  # Cache for material objects
        material_refs = {}  # Dictionary to track materials by reference key
        
        # 4. Iterate through columns and apply mapping rules
        for col_name, value in raw_row.items():
            # Skip empty values
            if value is None or str(value).strip() == "":
                continue
                
            # Find mapping rule for this column
            rule = mapping.match(col_name)
            if not rule:
                continue  # No mapping rule for this column
                
            table = rule["target_table"]
            target_field = rule["target_column"]
            kw = rule["extra_kwargs"]
            
            # Extract source column name for error messages
            source_column = col_name
            
            # Pre-process values for component calculations based on column names
            # This collects values needed for ratio-based calculations later
            if table == "concrete_mix" and target_field == "w_c_ratio":
                component_calcs['w_c_ratio'] = self._cast_decimal(value)
            elif table == "concrete_mix" and target_field == "notes":  
                if kw.get("prefix") == "Total Agg/Cement Ratio:":
                    component_calcs['total_agg_cement_ratio'] = self._cast_decimal(value)
                elif kw.get("prefix") == "Cement/Sand Ratio:":
                    component_calcs['cement_sand_ratio'] = self._cast_decimal(value)
                elif kw.get("prefix") == "RCA Replacement Level (%):":
                    component_calcs['rca_replacement_pct'] = self._cast_decimal(value)
            elif table == "mix_component" and kw.get("class_code") == "CEMENT":
                component_calcs['cement_kg_m3'] = self._cast_decimal(value)
            elif table == "bibliographic_reference":
                # Collect bibliographic data for later processing
                biblio_ref_data[target_field] = value
                
            try:
                # --- Handle different target tables ---
                
                # === CONCRETE MIX TABLE ===
                if table == "concrete_mix":
                    if target_field == "notes":
                        # Add to notes collection with optional prefix
                        prefix = kw.get("prefix", "")
                        note_text = f"{prefix}{value}".strip()
                        if note_text:
                            notes_list.append(note_text)
                            mix_updated = True
                    elif hasattr(mix_object, target_field):
                        # Cast value based on field type
                        if target_field in ["w_c_ratio", "w_b_ratio", "wb_k_reported", "target_slump_mm"]:
                            casted_value = self._cast_decimal(value)
                        elif target_field == "date_created":
                            # TODO: Add date parsing if needed
                            casted_value = value
                        else:
                            casted_value = value
                            
                        # Set attribute on mix object if cast successful
                        if casted_value is not None:
                            setattr(mix_object, target_field, casted_value)
                            
                            # If we're setting wb_k_reported, also set k_flag to True
                            if target_field == "wb_k_reported":
                                mix_object.k_flag = True
                                
                            mix_updated = True
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Field '{target_field}' not found on ConcreteMix model"
                        ))
                
                # === MIX COMPONENT TABLE ===
                elif table == "mix_component":
                    # Extract material information from mapping
                    specific_name = kw.get("specific_name", target_field)  # Default material name is in target_field
                    class_code = kw.get("class_code")
                    subtype_code = kw.get("subtype_code")
                    is_cementitious = kw.get("is_cementitious", False)
                    reference_key = kw.get("reference_key")  # Get the reference key if provided
                    
                    # Check if we should use dynamic naming from another column
                    source_type_column = kw.get("source_type_column")
                    if source_type_column:
                        # Get the type name from the specified column
                        src_name = raw_row.get(source_type_column, "").strip()
                        
                        if src_name:
                            # Sanitize the name: strip, lowercase, replace spaces with underscores
                            # Keep alphanumerics and /,-,_
                            clean_name = re.sub(r'[^\w/\-]', '_', src_name.lower())
                            clean_name = re.sub(r'\s+', '_', clean_name)
                            
                            # Safety truncation to 60 characters (database field limit)
                            if len(clean_name) > 60:
                                self.stdout.write(self.style.WARNING(
                                    f"Warning: Material name '{clean_name}' exceeds 60 characters and will be truncated"
                                ))
                                clean_name = clean_name[:60]
                            
                            # Use the sanitized name for both specific_name and subtype_code
                            specific_name = clean_name
                            subtype_code = clean_name
                            
                            self.stdout.write(f"Using dynamic material name from '{source_type_column}': {specific_name}")
                    
                    # Cast and validate dosage
                    dosage = self._cast_decimal(value)
                    if dosage is None or dosage < 0:  # Allow zero dosages (valid in some cases)
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Invalid dosage '{value}' for {specific_name}, skipping"
                        ))
                        continue
                    
                    # Use the helper function to get or create material
                    try:
                        material_object = get_or_create_material(
                            class_code=class_code,
                            subtype_code=subtype_code,
                            specific_name=specific_name,
                            extra={
                                "dataset": dataset.dataset_name
                            }
                        )
                        
                        # If this material has a reference key, store it for later use
                        if reference_key:
                            material_refs[reference_key] = material_object
                            self.stdout.write(f"Tracked material reference '{reference_key}': {material_object.specific_name} (ID: {material_object.material_id})")
                            
                        self.stdout.write(f"Using material: {specific_name} (Class: {class_code})")
                    except Exception as mat_error:
                        self.stdout.write(self.style.ERROR(
                            f"Error getting/creating Material '{specific_name}': {mat_error}"
                        ))
                        continue
                    
                    # Finally, create or update the MixComponent
                    try:
                        mc, mc_created = cdb.MixComponent.objects.using("cdb").update_or_create(
                            mix=mix_object,
                            material=material_object,
                            defaults={
                                'dosage_kg_m3': dosage,
                                'is_cementitious': is_cementitious
                            }
                        )
                        
                        if mc_created:
                            self.stdout.write(f"Added {specific_name} ({dosage} kg/m³) to mix {mix_code}")
                        else:
                            self.stdout.write(f"Updated {specific_name} ({dosage} kg/m³) in mix {mix_code}")
                    
                    except Exception as comp_error:
                        self.stdout.write(self.style.ERROR(
                            f"Error adding component '{specific_name}' to mix: {comp_error}"
                        ))
                
                # === MATERIAL TABLE ===
                elif table == "material":
                    # Get required parameters
                    class_code = kw.get("class_code")
                    subtype_code = kw.get("subtype_code") or target_field  # Use target field as default
                    specific_name = value  # Material name/value
                    
                    # Check for binding parameters
                    bind_to_reference = kw.get("bind_to_reference")
                    bind_to_study = kw.get("bind_to_study")
                    subtype_from_value = kw.get("subtype_from_value") == True
                    
                    # Get reference and study values if binding parameters are provided
                    reference_value = None
                    study_value = None
                    if bind_to_reference and bind_to_study:
                        reference_value = raw_row.get(bind_to_reference, "").strip()
                        study_value = raw_row.get(bind_to_study, "").strip()
                    
                    # Use value as subtype_code if specified
                    if subtype_from_value:
                        # Create a sanitized subtype_code from the specific_name
                        subtype_code = re.sub(r'[^\w/\-]', '_', specific_name.lower())
                        subtype_code = re.sub(r'\s+', '_', subtype_code)
                    
                    # Skip if no class code provided
                    if not class_code:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: No class_code provided for material mapping of {source_column}"
                        ))
                        continue
                    
                    # Create or get the material
                    try:
                        # Add reference and study to the material data if provided
                        extra_data = {
                            "source_dataset": dataset.dataset_name
                        }
                        
                        if reference_value and study_value:
                            extra_data["reference_no"] = reference_value
                            extra_data["study_no"] = study_value
                        
                        material = get_or_create_material(
                            class_code=class_code,
                            subtype_code=subtype_code,
                            specific_name=specific_name,
                            **extra_data
                        )
                        
                        self.stdout.write(f"Using material: {specific_name} (Class: {class_code})")
                        
                        # Store material reference for linking later
                        if reference_value and study_value:
                            # Create a unique key for this material
                            mat_key = f"{reference_value}:{study_value}:{specific_name}"
                            # Store in a dictionary for later use when processing material properties
                            if not hasattr(self, 'material_refs'):
                                self.material_refs = {}
                            self.material_refs[mat_key] = material
                            
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error creating/getting material: {e}"
                        ))
                
                # === MATERIAL PROPERTY TABLE ===
                elif table == "material_property":
                    # Simplified material property handling
                    property_name = kw.get("property_name")
                    property_group = kw.get("property_group")
                    material_id = kw.get("material_id")
                    material_ref_key = kw.get("material_ref_key")
                    
                    # Skip if missing required fields
                    if not property_name or not property_group:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Missing property_name or property_group in mapping for {source_column}"
                        ))
                        continue
                    
                    # Validate value and convert to numeric
                    value_num = self._cast_decimal(value)
                    if value_num is None:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Invalid numeric value '{value}' for material property {property_name}"
                        ))
                        continue

                    # Find the property in the PropertyDictionary
                    try:
                        prop_dict, created = cdb.PropertyDictionary.objects.using("cdb").get_or_create(
                            property_name=property_name,
                            defaults={
                                "display_name": property_name.replace("_", " ").title(),
                                "property_group": property_group
                            }
                        )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error creating property dictionary entry: {e}"
                        ))
                        continue
                        
                    # Find material either by direct ID or through reference key
                    material = None
                    
                    # First try reference key
                    if material_ref_key and material_ref_key in material_refs:
                        material = material_refs[material_ref_key]
                        self.stdout.write(f"Using material from reference key '{material_ref_key}' for property {property_name}")
                    # Then try direct material ID
                    elif material_id:
                        try:
                            material = cdb.Material.objects.using("cdb").get(material_id=material_id)
                        except cdb.Material.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f"Warning: Material ID {material_id} not found"
                            ))
                    
                    # If we don't have a material, skip this property
                    if not material:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: No material found for property {property_name}"
                        ))
                        continue
                    
                    # Create or update the property value
                    try:
                        mat_prop, created = cdb.MaterialProperty.objects.using("cdb").update_or_create(
                            material=material,
                            property_name=prop_dict,
                            defaults={
                                "value_num": value_num
                            }
                        )
                        
                        if created:
                            self.stdout.write(f"Added property {property_name}={property_value} to {material_object}")
                        else:
                            self.stdout.write(f"Updated property {property_name}={property_value} for {material_object}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error saving material property: {e}"
                        ))
                
                # === PERFORMANCE RESULT TABLE ===
                elif table == "performance_result":
                    # Extract performance test information
                    category = kw.get("category")
                    unit_id = kw.get("unit_id")
                    test_method_id = kw.get("test_method_id")
                    age_column_name = kw.get("age_column")
                    age_days = kw.get("age_days", 28)  # Default from mapping if no column specified
                    specimen_info_col = kw.get("specimen_info_col")  # DS2 specific - column with specimen info
                    
                    # Get age from age column if provided, otherwise use default from mapping
                    if age_column_name:
                        age_value = self._cast_int(raw_row.get(age_column_name))
                        if age_value is not None:
                            age_days = age_value
                    
                    # Get test value
                    value_num = self._cast_decimal(value)
                    
                    # Validate required values
                    if value_num is None:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Invalid value '{value}' for performance result, skipping"
                        ))
                        continue
                    
                    # Get specimen information if column specified
                    specimen_object = None
                    if specimen_info_col and specimen_info_col in raw_row:
                        specimen_info_str = raw_row.get(specimen_info_col)
                        if specimen_info_str:
                            # Parse specimen info to get shape and dimensions
                            shape, dimensions = parse_specimen_info(specimen_info_str)
                            if shape:
                                try:
                                    # Instead of creating separate Specimen records, we'll store the specimen info
                                    # and create it as part of the PerformanceResult creation
                                    # This addresses the not-null constraint on mix_id in the specimen table
                                    
                                    # Round dimensions to reduce floating point comparison issues
                                    rounded_diameter = round(dimensions.get('nominal_diameter_mm', 0), 1)
                                    rounded_length = round(dimensions.get('nominal_length_mm', 0), 1)
                                    
                                    # Instead of creating a separate specimen object, we'll use this data
                                    # when creating the performance result
                                    specimen_info = {
                                        'shape': shape,
                                        'nominal_diameter_mm': rounded_diameter,
                                        'nominal_length_mm': rounded_length,
                                        'notes': f"Parsed from: {specimen_info_str}"
                                    }
                                    
                                    # For consistency with the rest of the code, we'll store this in a dictionary
                                    # that looks like an object with attributes
                                    class SpecimenInfo:
                                        def __init__(self, info):
                                            self.__dict__.update(info)
                                    
                                    specimen_object = SpecimenInfo(specimen_info)
                                            
                                    self.stdout.write(f"Using specimen: {shape} {rounded_diameter}x{rounded_length} mm")
                                except Exception as spec_error:
                                    self.stdout.write(self.style.ERROR(
                                        f"Error creating/getting specimen: {spec_error}"
                                    ))
                    
                    # Validate that required test method and unit exist
                    try:
                        # Check if test method exists
                        if test_method_id and not cdb.TestMethod.objects.using("cdb").filter(test_method_id=test_method_id).exists():
                            self.stdout.write(self.style.WARNING(
                                f"Warning: TestMethod ID {test_method_id} does not exist in the database."
                            ))
                            # Continue anyway as we've created the test methods in handle()
                            
                        # Check if unit exists
                        if unit_id and not cdb.UnitLookup.objects.using("cdb").filter(unit_id=unit_id).exists():
                            self.stdout.write(self.style.WARNING(
                                f"Warning: Unit ID {unit_id} does not exist in the database."
                            ))
                            # Continue anyway as we've created the unit in handle()
                        
                        # Prepare defaults without specimen initially
                        defaults = {
                            'value_num': value_num,
                            'unit_id': unit_id  # Use ID for now
                        }
                        
                        # We'll create the specimen after creating the performance result
                        # This addresses the mix_id not-null constraint in the specimen table
                        
                        # Create or update the performance result
                        pr, pr_created = cdb.PerformanceResult.objects.using("cdb").update_or_create(
                            mix=mix_object,
                            category=category,
                            test_method_id=test_method_id,
                            age_days=age_days,
                            defaults=defaults
                        )
                        
                        if pr_created:
                            # Now create the specimen if specimen_object info is available
                            if specimen_object and hasattr(specimen_object, 'shape'):
                                try:
                                    # Create specimen directly linked to the mix
                                    specimen = cdb.Specimen.objects.using("cdb").create(
                                        mix=mix_object,
                                        shape=specimen_object.shape,
                                        nominal_diameter_mm=specimen_object.nominal_diameter_mm,
                                        nominal_length_mm=specimen_object.nominal_length_mm,
                                        notes=specimen_object.notes
                                    )
                                    
                                    # Update performance result to link to the specimen
                                    pr.specimen = specimen
                                    pr.save(using="cdb")
                                    
                                    self.stdout.write(
                                        f"Added {category} result: {value_num} at {age_days} days for mix {mix_code} using {specimen_object.shape} specimen"
                                    )
                                except Exception as spec_create_error:
                                    self.stdout.write(self.style.ERROR(
                                        f"Error creating specimen for performance result: {spec_create_error}"
                                    ))
                                    self.stdout.write(
                                        f"Added {category} result: {value_num} at {age_days} days for mix {mix_code} (without specimen)"
                                    )
                            else:
                                self.stdout.write(
                                    f"Added {category} result: {value_num} at {age_days} days for mix {mix_code}"
                                )
                        else:
                            self.stdout.write(
                                f"Updated {category} result: {value_num} at {age_days} days for mix {mix_code}"
                            )
                    except Exception as result_error:
                        self.stdout.write(self.style.ERROR(
                            f"Error adding performance result to mix: {result_error}"
                        ))
                
                # === MATERIAL PROPERTY TABLE ===
                elif table == "material_property":
                    # Extract the material type hint (RCA, NCA) and unit
                    material_type = kw.get("material_type_hint")
                    unit_id = kw.get("unit_id")
                    
                    if not material_type:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Missing material_type_hint for material property '{target_field}'"
                        ))
                        continue
                    
                    # Store the value in the aggregate_details dictionary for later processing
                    # We need to create the materials first before we can assign properties
                    property_value = self._cast_decimal(value)
                    if property_value is not None:
                        aggregate_details[material_type][target_field] = {
                            'value': property_value,
                            'unit_id': unit_id
                        }
                        self.stdout.write(f"Collected {material_type} property {target_field} = {property_value}")
                        
                # === AGGREGATE DETAIL TABLE ===
                elif table == "aggregate_detail":
                    # Simplify aggregate detail handling by using material references
                    material_id = kw.get("material_id")
                    material_ref_key = kw.get("material_ref_key")
                    field_name = target_field
                    
                    # Handle different detail fields (water_absorption_pct, d_upper_mm, etc.)
                    # Convert to appropriate type based on field name
                    if field_name in ["bulk_density_kg_m3", "water_absorption_pct", "fineness_modulus", "d_upper_mm", "d_lower_mm"]:
                        casted_value = self._cast_decimal(value)
                    else:
                        # Default to string
                        casted_value = value
                        
                    if casted_value is None:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Invalid value '{value}' for aggregate detail {field_name}"
                        ))
                        continue
                    
                    # Find material either by direct ID or through reference key
                    material = None
                    
                    # First try reference key
                    if material_ref_key and material_ref_key in material_refs:
                        material = material_refs[material_ref_key]
                        self.stdout.write(f"Using material from reference key '{material_ref_key}' for aggregate detail {field_name}")
                    # Then try direct material ID
                    elif material_id:
                        try:
                            material = cdb.Material.objects.using("cdb").get(material_id=material_id)
                        except cdb.Material.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f"Warning: Material ID {material_id} not found for aggregate detail"
                            ))
                    
                    # If we don't have a material, skip this property
                    if not material:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: No material found for aggregate detail {field_name}"
                        ))
                        continue
                    
                    # Get or create aggregate detail for this material
                    try:
                        agg_detail, created = cdb.AggregateDetail.objects.using("cdb").get_or_create(
                            material=material,
                            defaults={
                                "bulk_density_kg_m3": None,
                                "water_absorption_pct": None,
                                "fineness_modulus": None,
                                "d_upper_mm": None,
                                "d_lower_mm": None
                            }
                        )
                        
                        # Set the field value
                        try:
                            setattr(agg_detail, field_name, casted_value)
                            agg_detail.save(using="cdb")
                            self.stdout.write(f"Set {material.specific_name} detail {field_name} = {casted_value}")
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(
                                f"Error setting aggregate detail field {field_name}: {e}"
                            ))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error creating aggregate detail: {e}"
                        ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Error processing column '{col_name}' for table '{table}': {e}"
                ))
        
        # 5. Process component calculations (DS2 specific)
        try:
            cement_kg_m3 = component_calcs['cement_kg_m3']
            w_c_ratio = component_calcs['w_c_ratio']
            cement_sand_ratio = component_calcs['cement_sand_ratio']
            total_agg_cement_ratio = component_calcs['total_agg_cement_ratio']
            rca_replacement_pct = component_calcs['rca_replacement_pct']

            if cement_kg_m3 is not None:
                # Cache the cement material for reference
                if 'CEM I' not in material_objects:
                    try:
                        material_objects['CEM I'] = get_or_create_material(
                            class_code="CEMENT",
                            subtype_code="CEM I",
                            specific_name="CEM I",
                            extra={"dataset": dataset.dataset_name}
                        )
                    except Exception as mat_error:
                        self.stdout.write(self.style.ERROR(f"Error getting cement material: {mat_error}"))

                # Calculate Water dosage from w/c ratio
                if w_c_ratio is not None:
                    water_dosage = cement_kg_m3 * w_c_ratio
                    if water_dosage > 0:
                        try:
                            # Get or create WATER material
                            if 'WATER' not in material_objects:
                                material_objects['WATER'] = get_or_create_material(
                                    class_code="WATER",
                                    subtype_code="WATER",
                                    specific_name="Water",
                                    extra={"dataset": dataset.dataset_name}
                                )

                            # Create MixComponent for water
                            cdb.MixComponent.objects.using("cdb").update_or_create(
                                mix=mix_object,
                                material=material_objects['WATER'],
                                defaults={
                                    'dosage_kg_m3': water_dosage,
                                    'is_cementitious': False
                                }
                            )
                            self.stdout.write(f"Added WATER component: {water_dosage:.1f} kg/m³ to mix {mix_code}")
                        except Exception as water_err:
                            self.stdout.write(self.style.ERROR(f"Error adding water component: {water_err}"))

                # Calculate NFA (Sand) dosage from cement:sand ratio
                if cement_sand_ratio is not None and cement_sand_ratio > 0:
                    nfa_dosage = cement_kg_m3 / cement_sand_ratio
                    if nfa_dosage > 0:
                        try:
                            # Get or create NFA material
                            if 'NFA' not in material_objects:
                                material_objects['NFA'] = get_or_create_material(
                                    class_code="AGGR_F",
                                    subtype_code="NFA",
                                    specific_name="Natural Fine Aggregate",
                                    extra={"dataset": dataset.dataset_name}
                                )

                            # Create MixComponent for NFA
                            cdb.MixComponent.objects.using("cdb").update_or_create(
                                mix=mix_object,
                                material=material_objects['NFA'],
                                defaults={
                                    'dosage_kg_m3': nfa_dosage,
                                    'is_cementitious': False
                                }
                            )
                            self.stdout.write(f"Added NFA component: {nfa_dosage:.1f} kg/m³ to mix {mix_code}")
                        except Exception as nfa_err:
                            self.stdout.write(self.style.ERROR(f"Error adding NFA component: {nfa_err}"))

                # Calculate Total Aggregate dosage
                total_agg_dosage = None
                if total_agg_cement_ratio is not None:
                    total_agg_dosage = cement_kg_m3 * total_agg_cement_ratio
                    self.stdout.write(f"Calculated total aggregate: {total_agg_dosage:.1f} kg/m³")

                # Calculate Coarse Aggregate dosages (RCA and NCA)
                if total_agg_dosage is not None and nfa_dosage is not None:
                    total_coarse_agg = total_agg_dosage - nfa_dosage
                    
                    if total_coarse_agg > 0:
                        # Calculate RCA and NCA dosages based on replacement level
                        rca_dosage = 0
                        nca_dosage = total_coarse_agg
                        
                        if rca_replacement_pct is not None:
                            rca_dosage = total_coarse_agg * (rca_replacement_pct / 100)
                            nca_dosage = total_coarse_agg - rca_dosage
                            
                        # Create RCA component if dosage > 0
                        if rca_dosage > 0:
                            try:
                                # Get or create RCA material
                                if 'RCA' not in material_objects:
                                    material_objects['RCA'] = get_or_create_material(
                                        class_code="AGGR_C",
                                        subtype_code="RCA",
                                        specific_name="Recycled Coarse Aggregate",
                                        extra={"dataset": dataset.dataset_name}
                                    )

                                # Create MixComponent for RCA
                                cdb.MixComponent.objects.using("cdb").update_or_create(
                                    mix=mix_object,
                                    material=material_objects['RCA'],
                                    defaults={
                                        'dosage_kg_m3': rca_dosage,
                                        'is_cementitious': False
                                    }
                                )
                                self.stdout.write(f"Added RCA component: {rca_dosage:.1f} kg/m³ to mix {mix_code}")
                            except Exception as rca_err:
                                self.stdout.write(self.style.ERROR(f"Error adding RCA component: {rca_err}"))
                                
                        # Create NCA component if dosage > 0
                        if nca_dosage > 0:
                            try:
                                # Get or create NCA material
                                if 'NCA' not in material_objects:
                                    material_objects['NCA'] = get_or_create_material(
                                        class_code="AGGR_C",
                                        subtype_code="NCA",
                                        specific_name="Natural Coarse Aggregate",
                                        extra={"dataset": dataset.dataset_name}
                                    )

                                # Create MixComponent for NCA
                                cdb.MixComponent.objects.using("cdb").update_or_create(
                                    mix=mix_object,
                                    material=material_objects['NCA'],
                                    defaults={
                                        'dosage_kg_m3': nca_dosage,
                                        'is_cementitious': False
                                    }
                                )
                                self.stdout.write(f"Added NCA component: {nca_dosage:.1f} kg/m³ to mix {mix_code}")
                            except Exception as nca_err:
                                self.stdout.write(self.style.ERROR(f"Error adding NCA component: {nca_err}"))
        except Exception as calc_error:
            self.stdout.write(self.style.ERROR(f"Error in component calculations: {calc_error}"))
                
        # 6. Process aggregate details now that we have the material objects
        for agg_type, properties in aggregate_details.items():
            if agg_type in material_objects and properties:
                material_obj = material_objects[agg_type]
                
                for prop_name, prop_data in properties.items():
                    try:
                        if 'value' in prop_data:
                            # Create or update the aggregate detail
                            cdb.AggregateDetail.objects.using("cdb").update_or_create(
                                material=material_obj,
                                defaults={
                                    prop_name: prop_data['value']
                                }
                            )
                            self.stdout.write(f"Updated {agg_type} aggregate detail: {prop_name}={prop_data['value']}")
                    except Exception as agg_detail_err:
                        self.stdout.write(self.style.ERROR(
                            f"Error updating {agg_type} aggregate detail {prop_name}: {agg_detail_err}"
                        ))
        
        # 7. Process bibliographic reference if we have the required data
        try:
            if biblio_ref_data and 'citation_text' in biblio_ref_data:
                # Create or get the bibliographic reference
                biblio_ref, created = cdb.BibliographicReference.objects.using("cdb").get_or_create(
                    citation_text=biblio_ref_data['citation_text'],
                    defaults={
                        'author': biblio_ref_data.get('author', ''),
                        'year': self._cast_int(biblio_ref_data.get('year', None))
                    }
                )
                
                if created:
                    self.stdout.write(f"Created bibliographic reference: {biblio_ref_data['citation_text']}")
                else:
                    self.stdout.write(f"Using existing bibliographic reference: {biblio_ref_data['citation_text']}")
                    
                # Use raw SQL to check if the reference is already linked to the mix
                # This avoids Django ORM issues with composite primary keys
                with connections['cdb'].cursor() as cursor:
                    # Check if the link already exists
                    cursor.execute(
                        "SELECT 1 FROM concrete_mix_reference WHERE mix_id = %s AND reference_id = %s",
                        [mix_object.mix_id, biblio_ref.reference_id]
                    )
                    exists = cursor.fetchone() is not None
                    
                    # Create the link if it doesn't exist
                    if not exists:
                        cursor.execute(
                            "INSERT INTO concrete_mix_reference (mix_id, reference_id) VALUES (%s, %s)",
                            [mix_object.mix_id, biblio_ref.reference_id]
                        )
                self.stdout.write(f"Linked reference to mix {mix_code}")
        except Exception as biblio_err:
            self.stdout.write(self.style.ERROR(f"Error processing bibliographic reference: {biblio_err}"))
                
        # 8. Save updated mix with collected notes
        if mix_updated or notes_list:
            try:
                # Join the collected notes and set on mix object
                if notes_list:
                    mix_object.notes = "; ".join(notes_list)
                
                # Save the updated mix
                mix_object.save(using="cdb")
                self.stdout.write(f"Saved updates to mix {mix_code}")
            except Exception as save_error:
                self.stdout.write(self.style.ERROR(f"Error saving mix updates: {save_error}"))

    def _cast_decimal(self, value):
        """Cast string value to Decimal, handling various formats."""
        if value is None or str(value).strip() == '':
            return None
        try:
            # Handle potential comma decimal separator
            cleaned_value = str(value).replace(',', '.').strip()
            from decimal import Decimal
            return Decimal(cleaned_value)
        except (ValueError, decimal.InvalidOperation):
            self.stdout.write(self.style.WARNING(f"Warning: Could not cast '{value}' to Decimal."))
            return None
            
    def _cast_int(self, value):
        """Cast string value to Integer, handling various formats."""
        if value is None or str(value).strip() == '':
            return None
        try:
            # Handle potential floats like '28.0'
            return int(float(str(value).replace(',', '.').strip()))
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(f"Warning: Could not cast '{value}' to Integer."))
            return None

"""
############  Sample column_map_DS1.csv  #################
source_column,target_table,target_column,extra_kwargs
cement_kg_m3,mix_component,CEM I,{"class_code":"CEM"}
blas_furnace_slag_kg_m3,mix_component,GGBS,{"class_code":"SCM"}
fly_ash_kg_m3,mix_component,Fly Ash,{"class_code":"SCM"}
water_kg_m3,mix_component,Water,{"class_code":"H2O"}
natural_coarse_aggregate_kg_m3,mix_component,NCA,{"class_code":"AGG-C"}
natural_fine_aggregate_kg_m3,mix_component,NFA,{"class_code":"AGG-F"}
superplasticizer_kg_m3,mix_component,Superplasticizer,{"class_code":"ADM"}
fck_mpa,performance_result,compressive_strength,{"category":"hardened","test_method_id":1,"unit_id":(SELECT unit_id FROM unit_lookup WHERE unit_symbol='MPa')}
"""