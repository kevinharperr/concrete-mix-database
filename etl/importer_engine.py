#!/usr/bin/env python3

import os
import sys
import logging
import pandas as pd
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any, Tuple
from django.db import transaction
from django.db.models import Model

# Add the parent directory to the path so we can import Django modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import (
    Dataset, BibliographicReference, ConcreteMix, Material, MaterialClass,
    MixComponent, PerformanceResult, PropertyDictionary, TestMethod, UnitLookup,
    Specimen, CementDetail, AggregateDetail, ScmDetail, AdmixtureDetail
)


class DatasetImporter:
    """
    Generic dataset importer that uses configuration dictionaries to import
    concrete mix datasets into Django models.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the importer with a configuration dictionary."""
        self.config = config
        self.logger = self._setup_logging()
        
        # Caches to avoid redundant database queries
        self.material_cache = {}
        self.property_cache = {}
        self.unit_cache = {}
        self.test_method_cache = {}
        self.material_class_cache = {}
        self.specimen_cache = {}
        
        # Statistics tracking
        self.stats = {
            'total_rows': 0,
            'successful_mixes': 0,
            'failed_mixes': 0,
            'components_created': 0,
            'performance_results_created': 0,
            'validation_errors': 0
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the import process."""
        logger = logging.getLogger(f"DatasetImporter_{self.config['dataset_meta']['name'].replace(' ', '_')}")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers to prevent duplicates
        logger.handlers.clear()
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_django_object(self, model_class: Model, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Model, bool]:
        """Helper for get_or_create operations."""
        try:
            return model_class.objects.get_or_create(defaults=defaults or {}, **kwargs)
        except Exception as e:
            self.logger.error(f"Error getting/creating {model_class.__name__} with {kwargs}: {e}")
            raise
    
    def _ensure_base_lookups(self) -> None:
        """Ensure all required base lookup objects exist in the database."""
        self.logger.info("Ensuring base lookup objects exist...")
        
        # MaterialClass objects
        material_classes = set()
        for material_spec in self.config['materials']:
            material_classes.add(material_spec['material_class_code'])
        
        for class_code in material_classes:
            if class_code not in self.material_class_cache:
                class_name = self._get_material_class_name(class_code)
                material_class, created = self._get_django_object(
                    MaterialClass,
                    defaults={'class_name': class_name},
                    class_code=class_code
                )
                self.material_class_cache[class_code] = material_class
                if created:
                    self.logger.info(f"Created MaterialClass: {class_code} - {class_name}")
        
        # PropertyDictionary objects
        for perf_spec in self.config['performance_results']:
            property_pk = perf_spec['property_pk']
            if property_pk not in self.property_cache:
                property_obj, created = self._get_django_object(
                    PropertyDictionary,
                    defaults={
                        'display_name': self._get_property_display_name(property_pk),
                        'property_group': 'MECHANICAL'
                    },
                    property_name=property_pk
                )
                self.property_cache[property_pk] = property_obj
                if created:
                    self.logger.info(f"Created PropertyDictionary: {property_pk}")
        
        # UnitLookup objects
        for perf_spec in self.config['performance_results']:
            unit_symbol = perf_spec['unit_symbol']
            if unit_symbol not in self.unit_cache:
                unit_obj, created = self._get_django_object(
                    UnitLookup,
                    defaults={'description': f"Unit of measurement: {unit_symbol}"},
                    unit_symbol=unit_symbol
                )
                self.unit_cache[unit_symbol] = unit_obj
                if created:
                    self.logger.info(f"Created UnitLookup: {unit_symbol}")
        
        # TestMethod objects - UPDATED to use standardized test methods
        for perf_spec in self.config['performance_results']:
            test_method_desc = self._get_standardized_test_method_description(perf_spec)
            if test_method_desc not in self.test_method_cache:
                test_method, created = self._get_django_object(
                    TestMethod,
                    defaults={'clause': 'Various standards'},
                    description=test_method_desc
                )
                self.test_method_cache[test_method_desc] = test_method
                if created:
                    self.logger.info(f"Created TestMethod: {test_method_desc}")
    
    def _get_material_class_name(self, class_code: str) -> str:
        """Get display name for material class code."""
        class_names = {
            'CEMENT': 'Cement',
            'WATER': 'Water',
            'AGGR_C': 'Coarse Aggregate',
            'AGGR_F': 'Fine Aggregate',
            'SCM': 'Supplementary Cementitious Material',
            'ADM': 'Admixture',
            'MIN_ADD': 'Mineral Addition'
        }
        return class_names.get(class_code, class_code)
    
    def _get_property_display_name(self, property_pk: str) -> str:
        """Get display name for property key."""
        property_names = {
            'compressive_strength': 'Compressive Strength',
            'tensile_strength': 'Tensile Strength',
            'elastic_modulus': 'Elastic Modulus',
            'flexural_strength': 'Flexural Strength'
        }
        return property_names.get(property_pk, property_pk.replace('_', ' ').title())
    
    def _get_standardized_test_method_description(self, perf_spec: Dict) -> str:
        """
        Get standardized test method description to prevent fragmentation.
        
        For compressive strength, always use 'Compressive Strength Test' regardless
        of what the configuration specifies. Specimen details are stored separately.
        For slump flow, always use 'Slump Flow Test' for consistency.
        For slump, always use 'Slump Test' for consistency.
        """
        property_pk = perf_spec['property_pk']
        
        # Standardize compressive strength test method name
        if property_pk == 'compressive_strength':
            return 'Compressive Strength Test'
        
        # Standardize slump flow test method name
        if property_pk == 'slump_flow':
            return 'Slump Flow Test'
        
        # Standardize slump test method name
        if property_pk == 'slump':
            return 'Slump Test'
        
        # For other properties, you could add more standardization here
        # For now, use what's configured
        return perf_spec.get('test_method_description', f'{property_pk.replace("_", " ").title()} Test')
    
    def _create_or_update_dataset_meta(self) -> Dataset:
        """Create or update the Dataset and BibliographicReference objects."""
        self.logger.info("Creating/updating dataset metadata...")
        
        # Create BibliographicReference first
        biblio_data = self.config['dataset_meta']['bibliographic_reference']
        biblio_ref, created = self._get_django_object(
            BibliographicReference,
            defaults={
                'author': biblio_data['author'],
                'title': biblio_data['title'],
                'publication': biblio_data['publication'],
                'year': biblio_data['year'],
                'doi': biblio_data.get('doi'),
                'citation_text': biblio_data.get('citation_text')
            },
            doi=biblio_data.get('doi') or f"dataset_{self.config['dataset_meta']['name'].lower().replace(' ', '_')}"
        )
        
        if created:
            self.logger.info(f"Created BibliographicReference: {biblio_ref.title}")
        
        # Create Dataset
        dataset_meta = self.config['dataset_meta']
        dataset, created = self._get_django_object(
            Dataset,
            defaults={
                'description': dataset_meta['description'],
                'source': dataset_meta['source_text'],
                'year_published': dataset_meta['year_published'],
                'biblio_reference': biblio_ref
            },
            dataset_name=dataset_meta['name']
        )
        
        if created:
            self.logger.info(f"Created Dataset: {dataset.dataset_name}")
        
        return dataset
    
    def _get_or_create_material(self, material_spec: Dict, row_data: pd.Series, dataset_obj: Dataset) -> Optional[Material]:
        """Get or create a Material object based on configuration and row data."""
        try:
            # Create a dataset-specific cache key to avoid reusing materials across datasets
            cache_key = f"{dataset_obj.dataset_name}_{material_spec['material_class_code']}_{material_spec['fixed_properties'].get('specific_name', 'unknown')}"
            
            if cache_key in self.material_cache:
                return self.material_cache[cache_key]
            
            # Get MaterialClass
            material_class = self.material_class_cache[material_spec['material_class_code']]
            
            # Create Material (removed is_cementitious since it belongs to MixComponent)
            # Make materials dataset-specific by including dataset name in the query
            lookup_criteria = {
                'material_class': material_class,
                'source_dataset': dataset_obj.dataset_name,
                **material_spec['fixed_properties']
            }
            
            material, created = self._get_django_object(
                Material,
                defaults=lookup_criteria,
                **lookup_criteria
            )
            
            if created:
                self.logger.info(f"Created Material: {material.specific_name} for {dataset_obj.dataset_name}")
                
                # Create detail model if needed
                detail_data = material_spec.get('detail_model_data', {})
                if detail_data:
                    self._create_material_detail(material, detail_data, row_data)
            else:
                self.logger.debug(f"Using existing Material: {material.specific_name} for {dataset_obj.dataset_name}")
            
            self.material_cache[cache_key] = material
            return material
            
        except Exception as e:
            self.logger.error(f"Error creating material: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _create_material_detail(self, material: Material, detail_data: Dict, row_data: pd.Series) -> None:
        """Create the appropriate detail model for a material."""
        material_class_code = material.material_class.class_code
        
        try:
            if material_class_code == 'CEMENT':
                self._create_cement_detail(material, detail_data, row_data)
            elif material_class_code in ['AGGR_C', 'AGGR_F']:
                self._create_aggregate_detail(material, detail_data, row_data)
            elif material_class_code == 'SCM':
                self._create_scm_detail(material, detail_data, row_data)
            elif material_class_code == 'ADM':
                self._create_admixture_detail(material, detail_data, row_data)
                
        except Exception as e:
            self.logger.error(f"Error creating detail for material {material.specific_name}: {e}")
    
    def _create_cement_detail(self, material: Material, detail_data: Dict, row_data: pd.Series) -> None:
        """Create CementDetail for a cement material."""
        detail_fields = {}
        
        for field_name, field_config in detail_data.items():
            if isinstance(field_config, dict) and 'fixed_value' in field_config:
                detail_fields[field_name] = field_config['fixed_value']
            elif isinstance(field_config, dict) and 'csv_col' in field_config:
                csv_col = field_config['csv_col']
                if csv_col in row_data and pd.notna(row_data[csv_col]):
                    detail_fields[field_name] = self._safe_decimal(row_data[csv_col])
            elif field_config is not None:
                detail_fields[field_name] = field_config
        
        CementDetail.objects.get_or_create(
            material=material,
            defaults=detail_fields
        )
    
    def _create_aggregate_detail(self, material: Material, detail_data: Dict, row_data: pd.Series) -> None:
        """Create AggregateDetail for an aggregate material."""
        detail_fields = {}
        
        for field_name, field_config in detail_data.items():
            if isinstance(field_config, dict) and 'fixed_value' in field_config:
                detail_fields[field_name] = field_config['fixed_value']
            elif field_name.endswith('_csv_col'):
                # Handle CSV column references
                actual_field = field_name.replace('_csv_col', '')
                csv_col = field_config
                if csv_col in row_data and pd.notna(row_data[csv_col]):
                    detail_fields[actual_field] = self._safe_decimal(row_data[csv_col])
            elif field_config is not None:
                detail_fields[field_name] = field_config
        
        AggregateDetail.objects.get_or_create(
            material=material,
            defaults=detail_fields
        )
    
    def _create_scm_detail(self, material: Material, detail_data: Dict, row_data: pd.Series) -> None:
        """Create ScmDetail for an SCM material."""
        detail_fields = {}
        
        for field_name, field_config in detail_data.items():
            if isinstance(field_config, dict) and 'fixed_value' in field_config:
                detail_fields[field_name] = field_config['fixed_value']
            elif isinstance(field_config, dict) and 'csv_col' in field_config:
                csv_col = field_config['csv_col']
                if csv_col in row_data and pd.notna(row_data[csv_col]):
                    detail_fields[field_name] = self._safe_decimal(row_data[csv_col])
            elif field_config is not None:
                detail_fields[field_name] = field_config
        
        ScmDetail.objects.get_or_create(
            material=material,
            defaults=detail_fields
        )
    
    def _create_admixture_detail(self, material: Material, detail_data: Dict, row_data: pd.Series) -> None:
        """Create AdmixtureDetail for an admixture material."""
        detail_fields = {}
        
        for field_name, field_config in detail_data.items():
            if isinstance(field_config, dict) and 'fixed_value' in field_config:
                detail_fields[field_name] = field_config['fixed_value']
            elif isinstance(field_config, dict) and 'csv_col' in field_config:
                csv_col = field_config['csv_col']
                if csv_col in row_data and pd.notna(row_data[csv_col]):
                    detail_fields[field_name] = self._safe_decimal(row_data[csv_col])
            elif field_config is not None:
                detail_fields[field_name] = field_config
        
        AdmixtureDetail.objects.get_or_create(
            material=material,
            defaults=detail_fields
        )
    
    def _parse_specimen_string(self, specimen_string: str) -> Dict[str, Any]:
        """
        Parse specimen string from CSV and return specimen properties.
        
        Examples:
        - "4x8 Cylinder" -> {'shape': 'Cylinder', 'nominal_diameter_mm': 101.6, 'nominal_length_mm': 203.2}
        - "6x6x6 Cube" -> {'shape': 'Cube', 'nominal_diameter_mm': 152.4, 'nominal_length_mm': 152.4}
        - "4x4x12 Beam" -> {'shape': 'Beam', 'nominal_diameter_mm': 101.6, 'nominal_length_mm': 304.8}
        """
        if pd.isna(specimen_string) or not specimen_string:
            return {'shape': 'Unknown', 'nominal_diameter_mm': None, 'nominal_length_mm': None}
        
        specimen_string = str(specimen_string).strip()
        
        # Convert inches to mm
        inch_to_mm = Decimal('25.4')
        
        try:
            # Pattern for beam: "4x4x12 Beam" (width x height x length)
            beam_match = re.match(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*beam', specimen_string, re.IGNORECASE)
            if beam_match:
                width_inch = Decimal(beam_match.group(1))
                height_inch = Decimal(beam_match.group(2))
                length_inch = Decimal(beam_match.group(3))
                return {
                    'shape': 'Beam',
                    'nominal_diameter_mm': width_inch * inch_to_mm,  # Use width as "diameter"
                    'nominal_length_mm': length_inch * inch_to_mm
                }
            
            # Pattern for cylinder: "4x8 Cylinder"
            cylinder_match = re.match(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*cylinder', specimen_string, re.IGNORECASE)
            if cylinder_match:
                diameter_inch = Decimal(cylinder_match.group(1))
                length_inch = Decimal(cylinder_match.group(2))
                return {
                    'shape': 'Cylinder',
                    'nominal_diameter_mm': diameter_inch * inch_to_mm,
                    'nominal_length_mm': length_inch * inch_to_mm
                }
            
            # Pattern for cube: "6x6x6 Cube" or malformed "4x4x4 Cylinder"
            cube_match = re.match(r'(\d+(?:\.\d+)?)x\1x\1\s*(?:cube|cylinder)', specimen_string, re.IGNORECASE)
            if cube_match:
                side_inch = Decimal(cube_match.group(1))
                side_mm = side_inch * inch_to_mm
                shape = 'Cube'  # Always treat equal dimensions as cube regardless of label
                if 'cylinder' in specimen_string.lower():
                    self.logger.warning(f"Malformed specimen '{specimen_string}' - treating equal dimensions as Cube")
                return {
                    'shape': shape,
                    'nominal_diameter_mm': side_mm,  # For cube, use side length as "diameter"
                    'nominal_length_mm': side_mm
                }
            
            # Generic pattern for any shape with dimensions
            generic_match = re.search(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)', specimen_string)
            if generic_match:
                dim1_inch = Decimal(generic_match.group(1))
                dim2_inch = Decimal(generic_match.group(2))
                
                # Determine shape based on keywords
                if re.search(r'beam|prism', specimen_string, re.IGNORECASE):
                    shape = 'Beam'
                elif re.search(r'cube', specimen_string, re.IGNORECASE):
                    shape = 'Cube'
                else:
                    shape = 'Cylinder'  # Default assumption
                
                return {
                    'shape': shape,
                    'nominal_diameter_mm': dim1_inch * inch_to_mm,
                    'nominal_length_mm': dim2_inch * inch_to_mm
                }
            
            # Fallback for any other format
            self.logger.warning(f"Could not parse specimen string: {specimen_string}")
            return {'shape': 'Unknown', 'nominal_diameter_mm': None, 'nominal_length_mm': None}
            
        except Exception as e:
            self.logger.error(f"Error parsing specimen string '{specimen_string}': {e}")
            return {'shape': 'Unknown', 'nominal_diameter_mm': None, 'nominal_length_mm': None}
    
    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert a value to Decimal, returning None if conversion fails."""
        if pd.isna(value) or value == '':
            return None
        
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None
    
    def _validate_row(self, row_data: pd.Series) -> List[str]:
        """Validate a single row against the validation rules."""
        errors = []
        
        validation_rules = self.config.get('validation_rules', {})
        
        for column, rules in validation_rules.items():
            if column in row_data:
                value = row_data[column]
                if pd.notna(value):
                    try:
                        numeric_value = float(value)
                        if 'min' in rules and numeric_value < rules['min']:
                            errors.append(f"{column}: {numeric_value} < minimum {rules['min']}")
                        if 'max' in rules and numeric_value > rules['max']:
                            errors.append(f"{column}: {numeric_value} > maximum {rules['max']}")
                    except (ValueError, TypeError):
                        errors.append(f"{column}: Could not validate non-numeric value {value}")
        
        return errors
    
    def _create_concrete_mix(self, row_data: pd.Series, dataset_obj: Dataset) -> Optional[ConcreteMix]:
        """Create a ConcreteMix object from row data."""
        try:
            mix_fields = {'dataset': dataset_obj}
            
            # Map standard fields
            field_mappings = self.config['column_to_concretemix_fields']
            
            for csv_column, field_config in field_mappings.items():
                if csv_column == 'notes_from_columns':
                    continue  # Handle separately
                
                if isinstance(field_config, dict):
                    # Handle transformations like prefix addition
                    field_name = field_config['field']
                    if csv_column in row_data and pd.notna(row_data[csv_column]):
                        value = str(row_data[csv_column])
                        if 'prefix' in field_config:
                            value = field_config['prefix'] + value
                        mix_fields[field_name] = value
                else:
                    # Direct field mapping - handle both string and numeric fields
                    if csv_column in row_data and pd.notna(row_data[csv_column]):
                        value = row_data[csv_column]
                        # Try to convert to decimal for numeric fields, otherwise keep as string
                        decimal_value = self._safe_decimal(value)
                        if decimal_value is not None:
                            mix_fields[field_config] = decimal_value
                        else:
                            # Keep as string for non-numeric fields like region_country
                            mix_fields[field_config] = str(value).strip()
            
            # Calculate w_c_ratio and w_b_ratio from constituent columns
            self._calculate_ratios(row_data, mix_fields)
            
            # Build notes from multiple columns
            notes_parts = []
            notes_config = field_mappings.get('notes_from_columns', [])
            for note_spec in notes_config:
                csv_col = note_spec['csv_column']
                prefix = note_spec['prefix']
                if csv_col in row_data and pd.notna(row_data[csv_col]) and str(row_data[csv_col]).strip():
                    notes_parts.append(f"{prefix}{row_data[csv_col]}")
            
            if notes_parts:
                mix_fields['notes'] = '; '.join(notes_parts)
            
            # Create the mix
            concrete_mix = ConcreteMix.objects.create(**mix_fields)
            self.logger.debug(f"Created ConcreteMix: {concrete_mix.mix_code}")
            return concrete_mix
            
        except Exception as e:
            self.logger.error(f"Error creating ConcreteMix: {e}")
            return None
    
    def _calculate_ratios(self, row_data: pd.Series, mix_fields: Dict) -> None:
        """Calculate w_c_ratio and w_b_ratio from CSV columns."""
        try:
            # Find water column - look for common water column names
            water_columns = ['eff_water (kg/m3)', 'eff_water (kg/m3)  ', 'Eff. W/C ratio', 'water_content']
            water_value = None
            
            for col in water_columns:
                if col in row_data and pd.notna(row_data[col]):
                    if col == 'Eff. W/C ratio':
                        # This is already a ratio, not water content - round to 2 decimal places
                        mix_fields['w_c_ratio'] = round(float(self._safe_decimal(row_data[col])), 2)
                        mix_fields['w_b_ratio'] = mix_fields['w_c_ratio']  # For DS2 compatibility
                        return
                    else:
                        water_value = self._safe_decimal(row_data[col])
                        break
            
            if not water_value or water_value <= 0:
                self.logger.warning("No valid water content found for ratio calculation")
                return
            
            # Find cement content
            cement_columns = ['cement (kg/m3)', 'Cement Content kg/m^3']
            cement_value = None
            
            for col in cement_columns:
                if col in row_data and pd.notna(row_data[col]):
                    cement_value = self._safe_decimal(row_data[col])
                    break
            
            if not cement_value or cement_value <= 0:
                self.logger.warning("No valid cement content found for ratio calculation")
                return
            
            # Calculate w_c_ratio
            mix_fields['w_c_ratio'] = round(water_value / cement_value, 2)
            
            # Calculate w_b_ratio (water to binder ratio including SCMs)
            binder_total = cement_value
            
            # Add SCM contents to binder total
            scm_columns = ['fly ash (kg/m3)', 'silica fume (kg/m3)', 'BFS (kg/m3)', 'BFS (kg/m3) ']
            for col in scm_columns:
                if col in row_data and pd.notna(row_data[col]):
                    scm_value = self._safe_decimal(row_data[col])
                    if scm_value and scm_value > 0:
                        binder_total += scm_value
            
            # Calculate w_b_ratio
            if binder_total > 0:
                mix_fields['w_b_ratio'] = round(water_value / binder_total, 2)
            else:
                mix_fields['w_b_ratio'] = mix_fields['w_c_ratio']  # Fallback
                
            self.logger.debug(f"Calculated ratios - W/C: {mix_fields.get('w_c_ratio')}, W/B: {mix_fields.get('w_b_ratio')}")
            
        except Exception as e:
            self.logger.error(f"Error calculating ratios: {e}")
            # Set w_b_ratio same as w_c_ratio if calculation fails
            if 'w_c_ratio' in mix_fields:
                mix_fields['w_b_ratio'] = mix_fields['w_c_ratio']
    
    def _create_mix_components(self, concrete_mix: ConcreteMix, row_data: pd.Series, dataset_obj: Dataset) -> int:
        """Create MixComponent objects for a concrete mix."""
        components_created = 0
        
        for material_spec in self.config['materials']:
            # Skip if this material shouldn't create mix components
            if not material_spec.get('create_mix_component', True):
                continue
            
            # Get quantity from CSV
            quantity_column = material_spec.get('csv_column_for_quantity')
            if not quantity_column or quantity_column not in row_data:
                continue
            
            quantity = self._safe_decimal(row_data[quantity_column])
            if not quantity or quantity <= 0:
                continue
            
            # Get or create the material
            material = self._get_or_create_material(material_spec, row_data, dataset_obj)
            if not material:
                continue
            
            try:
                # Create MixComponent with is_cementitious from material configuration
                is_cementitious_value = material_spec.get('is_cementitious', False)
                self.logger.debug(f"Creating MixComponent for {material.specific_name} with is_cementitious={is_cementitious_value}")
                
                MixComponent.objects.create(
                    mix=concrete_mix,
                    material=material,
                    dosage_kg_m3=quantity,
                    is_cementitious=is_cementitious_value
                )
                components_created += 1
                self.logger.debug(f"Created MixComponent: {material.specific_name} - {quantity} kg/m³")
                
            except Exception as e:
                self.logger.error(f"Error creating MixComponent for {material.specific_name}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        return components_created
    
    def _create_performance_results(self, concrete_mix: ConcreteMix, row_data: pd.Series) -> int:
        """Create PerformanceResult objects for a concrete mix."""
        results_created = 0
        
        for perf_spec in self.config['performance_results']:
            value_column = perf_spec['csv_column_for_value']
            if value_column not in row_data:
                continue
            
            value = self._safe_decimal(row_data[value_column])
            if not value:
                continue
            
            try:
                # Handle specimen information - either from CSV parsing or fixed details
                specimen_data = self._get_specimen_data(perf_spec, row_data)
                
                # Create or get specimen
                specimen_key = f"{concrete_mix.mix_id}_{specimen_data['shape']}_{specimen_data['nominal_diameter_mm']}_{specimen_data['nominal_length_mm']}"
                
                if specimen_key not in self.specimen_cache:
                    specimen = Specimen.objects.create(
                        mix=concrete_mix,
                        shape=specimen_data['shape'],
                        nominal_diameter_mm=specimen_data['nominal_diameter_mm'],
                        nominal_length_mm=specimen_data['nominal_length_mm']
                    )
                    self.specimen_cache[specimen_key] = specimen
                else:
                    specimen = self.specimen_cache[specimen_key]
                
                # Get testing age - either from CSV column or fixed value
                age_days = self._get_testing_age(perf_spec, row_data)
                
                # Create PerformanceResult
                PerformanceResult.objects.create(
                    mix=concrete_mix,
                    property=self.property_cache[perf_spec['property_pk']],
                    value_num=value,
                    unit=self.unit_cache[perf_spec['unit_symbol']],
                    age_days=age_days,
                    test_method=self.test_method_cache[perf_spec['test_method_description']],
                    category=perf_spec['category'],
                    specimen=specimen
                )
                
                results_created += 1
                self.logger.debug(f"Created PerformanceResult: {perf_spec['property_pk']} = {value} {perf_spec['unit_symbol']} at {age_days} days")
                
            except Exception as e:
                self.logger.error(f"Error creating PerformanceResult: {e}")
        
        return results_created
    
    def _get_specimen_data(self, perf_spec: Dict, row_data: pd.Series) -> Dict[str, Any]:
        """Get specimen data either from fixed details or by parsing CSV column."""
        # Check if fixed specimen details are provided (for DS3)
        if 'specimen_details' in perf_spec:
            specimen_details = perf_spec['specimen_details']
            return {
                'shape': specimen_details['shape'],
                'nominal_diameter_mm': specimen_details['nominal_diameter_mm'],
                'nominal_length_mm': specimen_details['nominal_length_mm']
            }
        
        # Otherwise, parse from CSV column (for DS2 style)
        specimen_column = perf_spec.get('specimen_csv_column')
        if specimen_column and specimen_column in row_data:
            return self._parse_specimen_string(row_data[specimen_column])
        
        # Default fallback
        return {'shape': 'Unknown', 'nominal_diameter_mm': None, 'nominal_length_mm': None}
    
    def _get_testing_age(self, perf_spec: Dict, row_data: pd.Series) -> Optional[int]:
        """Get testing age either from CSV column or fixed value."""
        # Check if age comes from CSV column (for DS3)
        if 'csv_column_for_age' in perf_spec:
            age_column = perf_spec['csv_column_for_age']
            if age_column in row_data and pd.notna(row_data[age_column]):
                try:
                    return int(row_data[age_column])
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid age value in column {age_column}: {row_data[age_column]}")
                    return None
        
        # Otherwise use fixed age (for DS2 style)
        return perf_spec.get('fixed_age_days')
    
    def run_import(self) -> Dict[str, int]:
        """Run the complete import process."""
        self.logger.info(f"Starting import for {self.config['dataset_meta']['name']}")
        
        try:
            # Load CSV data
            csv_path = self.config['dataset_meta']['csv_file_path']
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
            df = pd.read_csv(csv_path)
            self.stats['total_rows'] = len(df)
            self.logger.info(f"Loaded {len(df)} rows from {csv_path}")
            
            # Setup base lookups and dataset metadata
            self._ensure_base_lookups()
            dataset_obj = self._create_or_update_dataset_meta()
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    with transaction.atomic():
                        # Validate row
                        validation_errors = self._validate_row(row)
                        if validation_errors:
                            self.logger.warning(f"Row {index + 1} validation errors: {'; '.join(validation_errors)}")
                            self.stats['validation_errors'] += len(validation_errors)
                        
                        # Create concrete mix
                        concrete_mix = self._create_concrete_mix(row, dataset_obj)
                        if not concrete_mix:
                            self.stats['failed_mixes'] += 1
                            continue
                        
                        # Create mix components
                        components_created = self._create_mix_components(concrete_mix, row, dataset_obj)
                        self.stats['components_created'] += components_created
                        
                        # Create performance results
                        results_created = self._create_performance_results(concrete_mix, row)
                        self.stats['performance_results_created'] += results_created
                        
                        self.stats['successful_mixes'] += 1
                        
                        if (index + 1) % 50 == 0:
                            self.logger.info(f"Processed {index + 1}/{len(df)} rows")
                            
                except Exception as e:
                    self.logger.error(f"Error processing row {index + 1}: {e}")
                    self.stats['failed_mixes'] += 1
                    continue
            
            # Print final statistics
            self._print_final_stats()
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            raise
    
    def _print_final_stats(self) -> None:
        """Print final import statistics."""
        self.logger.info("=" * 50)
        self.logger.info("IMPORT COMPLETED")
        self.logger.info("=" * 50)
        self.logger.info(f"Dataset: {self.config['dataset_meta']['name']}")
        self.logger.info(f"Total rows processed: {self.stats['total_rows']}")
        self.logger.info(f"Successful mixes: {self.stats['successful_mixes']}")
        self.logger.info(f"Failed mixes: {self.stats['failed_mixes']}")
        self.logger.info(f"Components created: {self.stats['components_created']}")
        self.logger.info(f"Performance results created: {self.stats['performance_results_created']}")
        self.logger.info(f"Validation errors: {self.stats['validation_errors']}")
        self.logger.info("=" * 50)


if __name__ == "__main__":
    print("This is the generic importer engine. Use run_specific_import.py to run imports.") 