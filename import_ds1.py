#!/usr/bin/env python
"""
Dataset 1 Import Script

This script imports Dataset 1 into the Concrete Mix Database with a focus on component completeness
and proper detail model integration. It's based on the DS1_DEFINITION.md mapping document and the
verified database schema in DB_SCHEMA.md.

Usage:
    python import_ds1.py
"""

import os
import sys
import csv
import logging
import django
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.db import transaction

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import models
from cdb_app.models import (
    Dataset, ConcreteMix, Material, MaterialClass, MixComponent, PropertyDictionary, 
    TestMethod, UnitLookup, PerformanceResult, CementDetail, ScmDetail, 
    AggregateDetail, AdmixtureDetail, BibliographicReference
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ds1_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DS1_IMPORT')

# Constants
SOURCE_FILE = 'etl/ds1.csv'
DATASET_NAME = 'Dataset 1'
DATASET_DESCRIPTION = 'A collection of 1030 laboratory-tested concrete mixes from Taiwan with varying cement, SCM, and aggregate contents, used for predicting compressive strength. Data originally compiled by I-Cheng Yeh. Strengths measured at various ages.'
DATASET_SOURCE = 'I-Cheng Yeh, Department of Civil Engineering, Chung-Hua University, Taiwan. Originally from UCI Machine Learning Repository, sourced from research paper.'
DATASET_YEAR = 1998
DATASET_PAPER = 'MODELING OF STRENGTH OF HIGH-PERFORMANCE CONCRETE USING ARTIFICIAL NEURAL NETWORKS'
DATASET_JOURNAL = 'Cement and Concrete Research'
DATASET_DOI = '10.1016/S0008-8846(98)00165-3'
DATASET_AUTHOR = 'I.-C. Yeh'
DATASET_CITATION = 'Yeh, I.-C. (1998). Modeling of strength of high-performance concrete using artificial neural networks. Cement and Concrete Research, 28(12), 1797-1808.'

# Lookup dictionaries for reference data
material_classes = {}
materials = {}
properties = {}
units = {}
test_methods = {}

# Component validation counters
component_counts = {
    'cement': 0,
    'slag': 0,
    'fly_ash': 0,
    'water': 0,
    'superplasticizer': 0,
    'coarse_aggregate': 0,
    'fine_aggregate': 0
}

# Data validation ranges - updated to match DS1_DEFINITION.md
VALIDATION_RANGES = {
    'cement_kg_m3': (100, 550),   # Updated from (200, 600) to match definition
    'water_kg_m3': (120, 240),   # Updated from (100, 300) to match definition
    'w_c_ratio': (0.3, 1.38),   # Updated upper bound from 1.0 to 1.38 to account for dataset extremes
    'w_b_ratio': (0.3, 1.38),   # Updated accordingly to match w_c_ratio range
    'strength_mpa': (20, 80),    # Updated upper bound from 100 to 80 to match definition
    'testing_age_days': [1, 3, 7, 14, 28, 56, 90, 100, 180, 270, 360, 365]  # Expanded to include all potential testing ages
}

# Constants for reference data
COMP_STRENGTH_PROP_NAME = "Compressive Strength"
TEST_METHOD_NAME_DS1 = "Standard Compression Test"
STRENGTH_UNIT_SYMBOL = "MPa"

def load_reference_data():
    """Load necessary reference data from the database and create any missing required records"""
    global material_classes, properties, units, test_methods
    
    # Required material classes for Dataset 1
    required_material_classes = [
        {'class_code': 'CEMENT', 'class_name': 'Cement'},
        {'class_code': 'SCM', 'class_name': 'Supplementary Cementitious Material'},
        {'class_code': 'WATER', 'class_name': 'Water'},
        {'class_code': 'ADM', 'class_name': 'Admixture'},
        {'class_code': 'AGGR_C', 'class_name': 'Coarse Aggregate'},
        {'class_code': 'AGGR_F', 'class_name': 'Fine Aggregate'}
    ]
    
    # Check and create required material classes
    for mc_data in required_material_classes:
        try:
            mc, created = MaterialClass.objects.get_or_create(
                class_code=mc_data['class_code'],
                defaults={'class_name': mc_data['class_name']}
            )
            if created:
                logger.info(f"Created missing material class: {mc.class_code} - {mc.class_name}")
        except Exception as e:
            logger.error(f"Error creating material class {mc_data['class_code']}: {str(e)}")
    
    # Load all material classes into memory
    material_classes.clear()
    for mc in MaterialClass.objects.all():
        material_classes[mc.class_code] = mc
        logger.info(f"Loaded material class: {mc.class_code} - {mc.class_name}")
    
    # Check for and create required property entries
    try:
        # Use a valid code as property_name (PK)
        COMP_STRENGTH_PROP_CODE = 'compressive_strength'
        strength_prop, created = PropertyDictionary.objects.get_or_create(
            property_name=COMP_STRENGTH_PROP_CODE,
            defaults={
                'display_name': COMP_STRENGTH_PROP_NAME,
                'property_group': PropertyDictionary.MECHANICAL,
            }
        )
        if created:
            logger.info(f"Created missing property: {strength_prop.property_name}")
    except Exception as e:
        logger.error(f"Error creating property: {str(e)}")
    
    # Load property dictionary entries
    properties.clear()
    for prop in PropertyDictionary.objects.all():
        properties[prop.property_name.lower()] = prop
    # Ensure we can refer to the strength property using our constant
    properties[COMP_STRENGTH_PROP_CODE.lower()] = strength_prop
    
    # Check for and create required units
    try:
        mpa_unit, created = UnitLookup.objects.get_or_create(
            unit_symbol=STRENGTH_UNIT_SYMBOL,
            defaults={
                'unit_name': 'Megapascal',
                'dimension': 'pressure'
            }
        )
        if created:
            logger.info(f"Created missing unit: {mpa_unit.unit_symbol}")
    except Exception as e:
        logger.error(f"Error creating unit: {str(e)}")
    
    # Load units
    units.clear()
    for unit in UnitLookup.objects.all():
        units[unit.unit_symbol.lower()] = unit
    
    # Check for and create required test methods
    try:
        test_method, created = TestMethod.objects.get_or_create(
            description=TEST_METHOD_NAME_DS1,
            defaults={}
        )
        if created:
            logger.info(f"Created missing test method: {test_method.description}")
    except Exception as e:
        logger.error(f"Error creating test method: {str(e)}")
    
    # Load test methods
    test_methods.clear()
for method in TestMethod.objects.all():
    if method.description: # Ensure description is not None before lowercasing
        test_methods[method.description.lower()] = method
    else:
        logger.warning(f"TestMethod with id {method.test_method_id} has no description, cannot cache by name.")

def create_or_get_bibliographic_reference():
    """Create or retrieve the bibliographic reference for Dataset 1"""
    try:
        # Try to find existing reference first
        try:
            reference = BibliographicReference.objects.get(
                title=DATASET_PAPER,
                year=DATASET_YEAR
            )
            logger.info(f"Found existing bibliographic reference: {reference}")
            
        except BibliographicReference.DoesNotExist:
            # Create new reference with detailed information from updated documentation
            reference = BibliographicReference.objects.create(
                author=DATASET_AUTHOR,
                title=DATASET_PAPER,
                publication=DATASET_JOURNAL,
                year=DATASET_YEAR,
                doi=DATASET_DOI,
                url=f"https://doi.org/{DATASET_DOI}",
                citation_text=DATASET_CITATION
            )
            logger.info(f"Created new bibliographic reference: {reference}")
            
        return reference
    
    except Exception as e:
        logger.error(f"Error creating bibliographic reference: {str(e)}")
        raise

def create_or_get_dataset():
    """Create or retrieve the Dataset 1 record with accurate metadata from DS1_DEFINITION.md"""
    try:
        # Get the current time for timestamps
        current_time = datetime.now()
        
        # Create or get the bibliographic reference
        biblio_reference = create_or_get_bibliographic_reference()
        
        # Try to get existing dataset first
        try:
            dataset = Dataset.objects.get(dataset_name=DATASET_NAME)
            logger.info(f"Found existing dataset record: {dataset.dataset_name}")
            
            # Update metadata fields
            dataset.description = DATASET_DESCRIPTION
            dataset.source = DATASET_SOURCE
            dataset.year_published = DATASET_YEAR
            dataset.biblio_reference = biblio_reference
            
            # Update the last_import_date
            dataset.last_import_date = current_time
            logger.info(f"Updated last_import_date to: {current_time}")
            
            dataset.save()
            logger.info(f"Updated dataset metadata for: {dataset.dataset_name}")
            
        except Dataset.DoesNotExist:
            # Create new dataset with original import_date
            dataset = Dataset.objects.create(
                dataset_name=DATASET_NAME,
                description=DATASET_DESCRIPTION,
                source=DATASET_SOURCE,
                year_published=DATASET_YEAR,
                biblio_reference=biblio_reference
                # import_date will be set automatically via auto_now_add
            )
            
            # Set last_import_date to current time
            dataset.last_import_date = current_time
            dataset.save()
            
            logger.info(f"Created new dataset record: {dataset.dataset_name}")
            logger.info(f"Source: {DATASET_SOURCE}")
            logger.info(f"Paper: {DATASET_PAPER} ({DATASET_YEAR})")
            logger.info(f"Bibliographic Reference: {biblio_reference}")
            
        return dataset
        
    except Exception as e:
        logger.error(f"Error creating/updating dataset: {str(e)}")
        raise

def create_or_get_material(class_code, specific_name, subtype_code=None):
    """Create or retrieve a material record"""
    try:
        # Clean up input parameters for consistency
        if specific_name:
            specific_name = specific_name.strip()
        if subtype_code:
            subtype_code = subtype_code.strip()
        
        # Generate a more robust key for the materials dictionary
        # Use lowercase and remove problematic characters
        safe_specific_name = specific_name.lower().replace(' ', '_').replace('-', '_')
        safe_subtype = (subtype_code or '').lower().replace(' ', '_').replace('-', '_')
        material_key = f"{class_code.upper()}::{safe_specific_name}::{safe_subtype}"
        
        # Check if we've already loaded this material
        if material_key in materials:
            return materials[material_key]
        
        # Get the material class
        if class_code not in material_classes:
            logger.error(f"Material class {class_code} not found")
            raise ValueError(f"Material class {class_code} not found")
        
        material_class = material_classes[class_code]
        
        # Create or get the material
        material, created = Material.objects.get_or_create(
            material_class=material_class,
            specific_name=specific_name,
            subtype_code=subtype_code
        )
        
        # Cache the material for future use
        materials[material_key] = material
        
        if created:
            logger.info(f"Created new material: {material.specific_name} ({material.material_class.class_code})")
        
        return material
    except Exception as e:
        logger.error(f"Error creating material: {str(e)}")
        raise

def create_cement_material(name="Portland Cement", subtype="CEM I", strength_class="42.5N"):
    """Create a cement material with its detail record"""
    try:
        # Create the material
        material = create_or_get_material("CEMENT", name, subtype)
        
        # Create or update the cement detail using update_or_create for simplicity
        cement_detail, created = CementDetail.objects.update_or_create(
            material=material,  # This is the lookup parameter
            defaults={
                'strength_class': strength_class  # This will be updated if record exists
            }
        )
        if created:
            logger.info(f"Created cement detail for {material.specific_name} with strength class {strength_class}")
        else:
            logger.info(f"Updated cement detail for {material.specific_name} with strength class {strength_class}")
            
        return material
    except Exception as e:
        logger.error(f"Error creating cement material: {str(e)}")
        raise

def create_scm_material(name, subtype, scm_type_code):
    """Create an SCM material with its detail record"""
    try:
        # Create the material
        material = create_or_get_material("SCM", name, subtype)
        
        # Create or update the SCM detail using update_or_create
        scm_detail, created = ScmDetail.objects.update_or_create(
            material=material,  # Lookup parameter
            defaults={
                'scm_type_code': scm_type_code  # Will be updated if record exists
            }
        )
        if created:
            logger.info(f"Created SCM detail for {material.specific_name} with type {scm_type_code}")
        else:
            logger.info(f"Updated SCM detail for {material.specific_name} with type {scm_type_code}")
            
        return material
    except Exception as e:
        logger.error(f"Error creating SCM material: {str(e)}")
        raise

def create_aggregate_material(name, subtype, d_lower, d_upper, fineness_modulus=None):
    """Create an aggregate material with its detail record"""
    try:
        # Determine if fine or coarse based on size
        class_code = "AGGR_F" if d_upper <= 4.0 else "AGGR_C"
        aggr_type = "fine" if class_code == "AGGR_F" else "coarse"
        
        # Create the material
        material = create_or_get_material(class_code, name, subtype)
        
        # Prepare defaults dictionary with optional fineness_modulus
        defaults = {
            'd_lower_mm': d_lower,
            'd_upper_mm': d_upper
        }
        
        # Add fineness_modulus if provided
        if fineness_modulus is not None:
            defaults['fineness_modulus'] = fineness_modulus
        
        # Create or update the aggregate detail using update_or_create
        agg_detail, created = AggregateDetail.objects.update_or_create(
            material=material,  # Lookup parameter
            defaults=defaults
        )
        
        # Log creation with fineness_modulus if applicable
        fm_info = f", fineness modulus {fineness_modulus}" if fineness_modulus is not None else ""
        if created:
            logger.info(f"Created {aggr_type} aggregate detail for {material.specific_name} with size range {d_lower}-{d_upper} mm{fm_info}")
        else:
            logger.info(f"Updated {aggr_type} aggregate detail for {material.specific_name} with size range {d_lower}-{d_upper} mm{fm_info}")
            
        return material
    except Exception as e:
        logger.error(f"Error creating aggregate material: {str(e)}")
        raise

def create_admixture_material(name, subtype, solid_content_pct=None, specific_gravity=None):
    """Create an admixture material with its detail record"""
    try:
        # Create the material
        material = create_or_get_material("ADM", name, subtype)
        
        # Prepare defaults dict with non-None values only
        defaults = {}
        if solid_content_pct is not None:
            defaults['solid_content_pct'] = solid_content_pct
        if specific_gravity is not None:
            defaults['specific_gravity'] = specific_gravity
            
        # Create or update the admixture detail using update_or_create
        adm_detail, created = AdmixtureDetail.objects.update_or_create(
            material=material,  # Lookup parameter
            defaults=defaults  # Will update only non-None fields if record exists
        )
        
        if created:
            logger.info(f"Created admixture detail for {material.specific_name}")
        else:
            logger.info(f"Updated admixture detail for {material.specific_name}")
            
        return material
    except Exception as e:
        logger.error(f"Error creating admixture material: {str(e)}")
        raise

def create_water_material(name="Mixing Water"):
    """Create a water material"""
    try:
        # Create the material
        material = create_or_get_material("WATER", name)
        return material
    except Exception as e:
        logger.error(f"Error creating water material: {str(e)}")
        raise

def create_mix_component(mix, material, quantity_kg_m3, notes=None):
    """Create a mix component record"""
    try:
        if quantity_kg_m3 and float(quantity_kg_m3) > 0:
            component = MixComponent.objects.create(
                mix=mix,
                material=material,
                dosage_kg_m3=quantity_kg_m3,
                notes=notes
            )
            logger.info(f"Created component: {material.specific_name} ({quantity_kg_m3} kg/m³)")
            return component
        return None
    except Exception as e:
        logger.error(f"Error creating mix component: {str(e)}")
        raise

def create_performance_result(mix, value, age_days):
    """Create a compressive strength performance result using predefined reference data"""
    try:
        # Get the property (compressive strength) from our cached dictionary
        # Use the code instead of the name for lookup
        strength_property = properties.get(COMP_STRENGTH_PROP_CODE.lower())
        if not strength_property:
            logger.error(f"Compressive strength property '{COMP_STRENGTH_PROP_CODE}' not found")
            raise ValueError(f"Compressive strength property '{COMP_STRENGTH_PROP_CODE}' not found")
        
        # Get the unit (MPa) from our cached dictionary
        mpa_unit = units.get(STRENGTH_UNIT_SYMBOL.lower())
        if not mpa_unit:
            logger.error(f"Unit '{STRENGTH_UNIT_SYMBOL}' not found")
            raise ValueError(f"Unit '{STRENGTH_UNIT_SYMBOL}' not found")
        
        # Get the specific test method from our cached dictionary
        test_method = test_methods.get(TEST_METHOD_NAME_DS1.lower())
        if not test_method:
            logger.error(f"Test method '{TEST_METHOD_NAME_DS1}' not found")
            raise ValueError(f"Test method '{TEST_METHOD_NAME_DS1}' not found")
        
        # Create the performance result - use the property field now that it exists
        result = PerformanceResult.objects.create(
            mix=mix,
            property=strength_property,  # Now using the property field
            category=PerformanceResult.HARDENED,
            age_days=age_days,
            value_num=value,
            unit=mpa_unit,
            test_method=test_method
        )
        logger.info(f"Created performance result: {value} {STRENGTH_UNIT_SYMBOL} at {age_days} days")
        return result
    except Exception as e:
        logger.error(f"Error creating performance result: {str(e)}")
        raise

def validate_mix_components(mix):
    """Validate that a mix has all expected components"""
    components = mix.components.all()
    component_materials = [c.material.material_class.class_code for c in components]
    
    # Required components
    required = {
        'CEMENT': "Cement is missing", 
        'WATER': "Water is missing"
    }
    
    # At least one aggregate is required
    if 'AGGR_C' not in component_materials and 'AGGR_F' not in component_materials:
        logger.warning(f"Mix {mix.mix_id} is missing both coarse and fine aggregates")
    
    # Check required components
    for req_class, message in required.items():
        if req_class not in component_materials:
            logger.warning(f"Mix {mix.mix_id}: {message}")

def validate_detail_models():
    """Validate that all materials have appropriate detail models"""
    # Check Cement materials
    cement_materials = Material.objects.filter(material_class__class_code='CEMENT')
    for material in cement_materials:
        try:
            detail = material.cement_detail
        except CementDetail.DoesNotExist:
            logger.warning(f"Cement material {material.material_id} missing detail record")
    
    # Check SCM materials
    scm_materials = Material.objects.filter(material_class__class_code='SCM')
    for material in scm_materials:
        try:
            detail = material.scm_detail
        except ScmDetail.DoesNotExist:
            logger.warning(f"SCM material {material.material_id} missing detail record")
    
    # Check Aggregate materials
    aggregate_materials = Material.objects.filter(
        material_class__class_code__in=['AGGR_C', 'AGGR_F']
    )
    for material in aggregate_materials:
        try:
            detail = material.aggregate_detail
        except AggregateDetail.DoesNotExist:
            logger.warning(f"Aggregate material {material.material_id} missing detail record")
    
    # Check Admixture materials
    admixture_materials = Material.objects.filter(material_class__class_code='ADM')
    for material in admixture_materials:
        try:
            detail = material.admixture_detail
        except AdmixtureDetail.DoesNotExist:
            logger.warning(f"Admixture material {material.material_id} missing detail record")

def validate_data_ranges(row, mix_id):
    """Validate that data values fall within expected ranges for Dataset 1"""
    warnings = []
    
    # Check cement content
    cement_kg_m3 = Decimal(row.get('cement_kg_m3', 0))
    min_cement, max_cement = VALIDATION_RANGES['cement_kg_m3']
    if cement_kg_m3 > 0 and (cement_kg_m3 < min_cement or cement_kg_m3 > max_cement):
        warnings.append(f"Mix {mix_id}: Cement content {cement_kg_m3} kg/m³ outside expected range ({min_cement}-{max_cement})")
    
    # Check water content
    water_kg_m3 = Decimal(row.get('water_kg_m3', 0))
    min_water, max_water = VALIDATION_RANGES['water_kg_m3']
    if water_kg_m3 > 0 and (water_kg_m3 < min_water or water_kg_m3 > max_water):
        warnings.append(f"Mix {mix_id}: Water content {water_kg_m3} kg/m³ outside expected range ({min_water}-{max_water})")
    
    # Check w/c ratio
    w_c_ratio = Decimal(row.get('water_cement_ratio', 0))
    min_wc, max_wc = VALIDATION_RANGES['w_c_ratio']
    if w_c_ratio > 0 and (w_c_ratio < min_wc or w_c_ratio > max_wc):
        warnings.append(f"Mix {mix_id}: w/c ratio {w_c_ratio} outside expected range ({min_wc}-{max_wc})")
    
    # Check w/b ratio
    w_b_ratio = Decimal(row.get('water_binder_ratio', 0))
    min_wb, max_wb = VALIDATION_RANGES['w_b_ratio']
    if w_b_ratio > 0 and (w_b_ratio < min_wb or w_b_ratio > max_wb):
        warnings.append(f"Mix {mix_id}: w/b ratio {w_b_ratio} outside expected range ({min_wb}-{max_wb})")
    
    # Check strength value
    strength = Decimal(row.get('fck_mpa', 0))
    min_strength, max_strength = VALIDATION_RANGES['strength_mpa']
    if strength > 0 and (strength < min_strength or strength > max_strength):
        warnings.append(f"Mix {mix_id}: Strength {strength} MPa outside expected range ({min_strength}-{max_strength})")
    
    # Check testing age
    age_days = int(row.get('testing_age', 0))
    valid_ages = VALIDATION_RANGES['testing_age_days']
    if age_days > 0 and age_days not in valid_ages:
        warnings.append(f"Mix {mix_id}: Testing age {age_days} days not in expected values {valid_ages}")
    
    # Validate ratio consistency
    if cement_kg_m3 > 0 and water_kg_m3 > 0:
        calculated_wc = water_kg_m3 / cement_kg_m3
        if abs(calculated_wc - w_c_ratio) > 0.01:  # Allow small rounding differences
            warnings.append(f"Mix {mix_id}: Calculated w/c ratio {calculated_wc:.2f} doesn't match provided value {w_c_ratio}")
    
    # Calculate total cementitious content and validate w/b ratio
    slag_kg_m3 = Decimal(row.get('blas_furnace_slag_kg_m3', 0))
    fly_ash_kg_m3 = Decimal(row.get('fly_ash_kg_m3', 0))
    total_binder = cement_kg_m3 + slag_kg_m3 + fly_ash_kg_m3
    
    if total_binder > 0 and water_kg_m3 > 0:
        calculated_wb = water_kg_m3 / total_binder
        if abs(calculated_wb - w_b_ratio) > 0.01:  # Allow small rounding differences
            warnings.append(f"Mix {mix_id}: Calculated w/b ratio {calculated_wb:.2f} doesn't match provided value {w_b_ratio}")
    
    # Validate coarse/fine aggregate ratio
    ca_kg_m3 = Decimal(row.get('natural_coarse_aggregate_kg_m3', 0))
    fa_kg_m3 = Decimal(row.get('natural_fine_aggregate_kg_m3', 0))
    ca_fa_ratio = Decimal(row.get('coarse-agg_fine-agg_ratio', 0))
    
    if ca_kg_m3 > 0 and fa_kg_m3 > 0:
        calculated_ca_fa = ca_kg_m3 / fa_kg_m3
        if abs(calculated_ca_fa - ca_fa_ratio) > 0.02:  # Allow slightly larger tolerance for aggregates
            warnings.append(f"Mix {mix_id}: Calculated CA/FA ratio {calculated_ca_fa:.2f} doesn't match provided value {ca_fa_ratio}")
    
    # Log any warnings
    for warning in warnings:
        logger.warning(warning)
    
    return len(warnings) == 0

def import_dataset():
    """Main function to import Dataset 1"""
    logger.info("Starting Dataset 1 import process")
    
    # Load reference data
    logger.info("Loading reference data")
    load_reference_data()
    
    # Create or get the dataset
    dataset = create_or_get_dataset()
    
    # Create standard materials that will be reused
    logger.info("Creating standard materials")
    cement = create_cement_material()
    slag = create_scm_material("Ground Granulated Blast Furnace Slag", "GGBS", "GGBS")
    fly_ash = create_scm_material("Fly Ash", "FA", "FA")
    water = create_water_material()
    superplasticizer = create_admixture_material("Superplasticizer", "ASTM C494 Type G", 40.0, 1.1)
    coarse_aggregate = create_aggregate_material("Natural Coarse Aggregate", "NCA", 4.0, 20.0)
    fine_aggregate = create_aggregate_material("Natural Fine Aggregate", "NFA", 0.0, 4.0, fineness_modulus=Decimal('3.0'))
    
    # Process the CSV file
    logger.info(f"Reading source file: {SOURCE_FILE}")
    with open(SOURCE_FILE, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        mix_count = 0
        
        # Use a transaction for better performance and data integrity
        with transaction.atomic():
            for i, row in enumerate(reader, 1):
                try:
                    # Validate data ranges
                    if not validate_data_ranges(row, i):
                        logger.warning(f"Skipping row {i} due to validation errors")
                        continue
                    
                    # Extract mix data
                    w_c_ratio = Decimal(row.get('water_cement_ratio', 0))
                    w_b_ratio = Decimal(row.get('water_binder_ratio', 0))
                    ca_fa_ratio = row.get('coarse-agg_fine-agg_ratio', '')
                    sp_pct = row.get('superplasticizer_percentage_weight_of_cement_%', '')
                    
                    # Build notes field
                    notes = ""
                    if ca_fa_ratio:
                        notes += f"CA/FA ratio: {ca_fa_ratio}\n"
                    if sp_pct:
                        notes += f"SP % of cement: {sp_pct}\n"
                    
                    # Create the mix record
                    mix = ConcreteMix.objects.create(
                        dataset=dataset,
                        mix_code=f"DS1-{i}",
                        w_c_ratio=w_c_ratio,
                        w_b_ratio=w_b_ratio,
                        notes=notes
                    )
                    logger.info(f"Created mix: DS1-{i}")
                    mix_count += 1
                    
                    # Extract component quantities
                    cement_qty = Decimal(row.get('cement_kg_m3', 0))
                    slag_qty = Decimal(row.get('blas_furnace_slag_kg_m3', 0))
                    fly_ash_qty = Decimal(row.get('fly_ash_kg_m3', 0))
                    water_qty = Decimal(row.get('water_kg_m3', 0))
                    sp_qty = Decimal(row.get('superplasticizer_kg_m3', 0))
                    ca_qty = Decimal(row.get('natural_coarse_aggregate_kg_m3', 0))
                    fa_qty = Decimal(row.get('natural_fine_aggregate_kg_m3', 0))
                    
                    # Create components
                    if cement_qty > 0:
                        create_mix_component(mix, cement, cement_qty)
                        component_counts['cement'] += 1
                    
                    if slag_qty > 0:
                        create_mix_component(mix, slag, slag_qty)
                        component_counts['slag'] += 1
                    
                    if fly_ash_qty > 0:
                        create_mix_component(mix, fly_ash, fly_ash_qty)
                        component_counts['fly_ash'] += 1
                    
                    if water_qty > 0:
                        create_mix_component(mix, water, water_qty)
                        component_counts['water'] += 1
                    
                    if sp_qty > 0:
                        create_mix_component(mix, superplasticizer, sp_qty)
                        component_counts['superplasticizer'] += 1
                    
                    if ca_qty > 0:
                        create_mix_component(mix, coarse_aggregate, ca_qty)
                        component_counts['coarse_aggregate'] += 1
                    
                    if fa_qty > 0:
                        create_mix_component(mix, fine_aggregate, fa_qty)
                        component_counts['fine_aggregate'] += 1
                    
                    # Create performance result
                    strength = Decimal(row.get('fck_mpa', 0))
                    age_days = int(row.get('testing_age', 28))
                    if strength > 0:
                        create_performance_result(mix, strength, age_days)
                    
                    # Validate this mix has all required components
                    validate_mix_components(mix)
                    
                except Exception as e:
                    logger.error(f"Error processing row {i}: {str(e)}")
                    continue
    
    # Log import statistics
    logger.info(f"Import complete. Created {mix_count} mixes")
    logger.info(f"Component counts:")
    for component, count in component_counts.items():
        logger.info(f"  {component}: {count}")
    
    # Validate detail models were created properly
    validate_detail_models()
    
    return mix_count

if __name__ == "__main__":
    try:
        mix_count = import_dataset()
        logger.info(f"Successfully imported Dataset 1 with {mix_count} mixes")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        sys.exit(1)
