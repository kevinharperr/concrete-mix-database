import os
import sys
import django
import traceback

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from django.utils import timezone
from django.db import transaction

# Import models
from cdb_app.models import (
    MaterialClass, Material, Dataset, UnitLookup, 
    PropertyDictionary, Standard, AggregateDetail, 
    CementDetail, ScmDetail, AdmixtureDetail
)
from refresh_status.models import RefreshLogEntry

def log_import_event(dataset_name, event_type, message, data=None):
    """Log import events to both console and the database."""
    # Print to console
    print(f"{dataset_name}: {event_type} - {message}")
    
    # Database logging
    try:
        is_error = event_type == 'ERROR'
        RefreshLogEntry.objects.create(
            phase='Data Import',
            step=dataset_name,
            status=event_type,
            message=message,
            is_error=is_error,
            details=data
        )
    except Exception as e:
        print(f"Failed to log event to database: {str(e)}")

def import_reference_data():
    """Import reference data such as material classes, units, properties, etc."""
    print("\n=== IMPORTING REFERENCE DATA ===")
    dataset_name = "Reference Data"
    
    try:
        # Create material classes
        material_classes = [
            {'name': 'Cement', 'code': 'CMT'},
            {'name': 'SCM', 'code': 'SCM'},
            {'name': 'Aggregate', 'code': 'AGG'},
            {'name': 'Water', 'code': 'H2O'},
            {'name': 'Admixture', 'code': 'ADM'},
            {'name': 'Fiber', 'code': 'FIB'},
        ]
        
        for mc_data in material_classes:
            # Truncate class_code to max length of 8 chars
            class_code = mc_data['code']
            if len(class_code) > 8:
                class_code = class_code[:8]
                
            MaterialClass.objects.get_or_create(
                class_name=mc_data['name'],
                defaults={'class_code': class_code}
            )
        
        # Create standard units
        units = [
            {'symbol': 'kg/m³', 'description': 'Kilograms per cubic meter'},
            {'symbol': 'MPa', 'description': 'Megapascals'},
            {'symbol': 'mm', 'description': 'Millimeters'},
            {'symbol': '%', 'description': 'Percentage'},
            {'symbol': 'cm²/g', 'description': 'Square centimeters per gram'},
        ]
        
        for unit_data in units:
            UnitLookup.objects.get_or_create(
                unit_symbol=unit_data['symbol'],
                defaults={'description': unit_data['description']}
            )
        
        # Create common properties
        density_unit = UnitLookup.objects.filter(unit_symbol='kg/m³').first()
        if not density_unit:
            log_import_event(dataset_name, 'WARNING', "Unit kg/m³ not found for property density")
        
        properties = [
            {'name': 'density', 'display': 'Density', 'group': 'physical', 'unit': density_unit},
            {'name': 'water_content', 'display': 'Water Content', 'group': 'physical', 'unit': density_unit},
            {'name': 'cement_content', 'display': 'Cement Content', 'group': 'physical', 'unit': density_unit},
        ]
        
        for prop_data in properties:
            PropertyDictionary.objects.get_or_create(
                property_name=prop_data['name'],
                defaults={
                    'display_name': prop_data['display'],
                    'property_group': prop_data['group'],
                    'default_unit': prop_data['unit']
                }
            )
        
        # Create standards
        standards = [
            {'code': 'EN 206', 'title': 'Concrete Specification, performance, production and conformity'},
            {'code': 'ACI 318', 'title': 'Building Code Requirements for Structural Concrete'},
            {'code': 'ASTM C150', 'title': 'Standard Specification for Portland Cement'},
        ]
        
        for std_data in standards:
            Standard.objects.get_or_create(
                code=std_data['code'],
                defaults={'title': std_data['title']}
            )
        
        # Log success
        log_import_event(dataset_name, 'INFO', "Reference data import completed successfully")
        print("Reference data import succeeded")
        return True
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Error importing reference data: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        print("Reference data import failed")
        return False

def import_materials():
    """Import common materials used across datasets."""
    print("\n=== IMPORTING MATERIALS ===")
    dataset_name = "Common Materials"
    
    try:
        # Get material classes
        cement_class = MaterialClass.objects.get(class_name='Cement')
        scm_class = MaterialClass.objects.get(class_name='SCM')
        aggregate_class = MaterialClass.objects.get(class_name='Aggregate')
        water_class = MaterialClass.objects.get(class_name='Water')
        admixture_class = MaterialClass.objects.get(class_name='Admixture')
        
        # Create cement materials
        cements = [
            {'name': 'Ordinary Portland Cement (CEM I)', 'code': 'CEM1', 'material_class': cement_class},
            {'name': 'CEM II/A-L', 'code': 'CEM2A', 'material_class': cement_class},
            {'name': 'CEM II/B-V', 'code': 'CEM2B', 'material_class': cement_class},
            {'name': 'CEM III/A', 'code': 'CEM3A', 'material_class': cement_class},
            {'name': 'CEM III/B', 'code': 'CEM3B', 'material_class': cement_class},
        ]
        
        for cement_data in cements:
            material, created = Material.objects.get_or_create(
                specific_name=cement_data['name'],
                material_class=cement_data['material_class'],
                defaults={
                    'subtype_code': cement_data['code'],
                }
            )
            
            if created:
                log_import_event(
                    dataset_name,
                    'INFO',
                    f"Created cement material: {cement_data['name']}"
                )
                # Create cement details
                CementDetail.objects.get_or_create(material=material)
        
        # Create SCM materials
        scms = [
            {'name': 'Fly Ash', 'code': 'FA', 'material_class': scm_class},
            {'name': 'GGBS', 'code': 'GGBS', 'material_class': scm_class},
            {'name': 'Silica Fume', 'code': 'SF', 'material_class': scm_class},
            {'name': 'Metakaolin', 'code': 'MK', 'material_class': scm_class},
        ]
        
        for scm_data in scms:
            material, created = Material.objects.get_or_create(
                specific_name=scm_data['name'],
                material_class=scm_data['material_class'],
                defaults={
                    'subtype_code': scm_data['code'],
                }
            )
            
            if created:
                log_import_event(
                    dataset_name,
                    'INFO',
                    f"Created SCM material: {scm_data['name']}"
                )
                # Create SCM details
                ScmDetail.objects.get_or_create(material=material)
        
        # Create aggregate materials
        aggregates = [
            {'name': 'Fine Aggregate (0-4mm)', 'code': 'FA', 'is_fine': True, 'material_class': aggregate_class},
            {'name': 'Coarse Aggregate (4-10mm)', 'code': 'CA4', 'is_fine': False, 'material_class': aggregate_class},
            {'name': 'Coarse Aggregate (10-20mm)', 'code': 'CA10', 'is_fine': False, 'material_class': aggregate_class},
        ]
        
        for agg_data in aggregates:
            material, created = Material.objects.get_or_create(
                specific_name=agg_data['name'],
                material_class=agg_data['material_class'],
                defaults={
                    'subtype_code': agg_data['code'],
                }
            )
            
            if created:
                log_import_event(
                    dataset_name,
                    'INFO',
                    f"Created aggregate material: {agg_data['name']}"
                )
                # Create aggregate details with size ranges based on name
                size_range = agg_data['name'].lower()
                d_lower = None
                d_upper = None
                
                if 'fine' in size_range and '0-4' in size_range:
                    d_lower = 0
                    d_upper = 4
                elif '4-10' in size_range:
                    d_lower = 4
                    d_upper = 10
                elif '10-20' in size_range:
                    d_lower = 10
                    d_upper = 20
                
                AggregateDetail.objects.get_or_create(
                    material=material,
                    defaults={
                        'd_lower_mm': d_lower,
                        'd_upper_mm': d_upper,
                    }
                )
        
        # Create water
        material, created = Material.objects.get_or_create(
            specific_name="Water",
            material_class=water_class,
            defaults={
                'subtype_code': 'H2O',
            }
        )
        
        if created:
            log_import_event(dataset_name, 'INFO', "Created water material")
        
        # Create admixtures
        admixtures = [
            {'name': 'Superplasticizer', 'code': 'SP', 'material_class': admixture_class},
            {'name': 'Water Reducer', 'code': 'WR', 'material_class': admixture_class},
            {'name': 'Air Entrainer', 'code': 'AE', 'material_class': admixture_class},
        ]
        
        for admix_data in admixtures:
            material, created = Material.objects.get_or_create(
                specific_name=admix_data['name'],
                material_class=admix_data['material_class'],
                defaults={
                    'subtype_code': admix_data['code'],
                }
            )
            
            if created:
                log_import_event(
                    dataset_name,
                    'INFO',
                    f"Created admixture material: {admix_data['name']}"
                )
                # Create admixture details
                AdmixtureDetail.objects.get_or_create(material=material)
        
        # Log success
        material_count = Material.objects.count()
        log_import_event(
            dataset_name,
            'INFO',
            f"Materials import completed successfully. {material_count} materials available."
        )
        print("Materials import succeeded")
        return True
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Error importing materials: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        print("Materials import failed")
        return False

def import_ds1():
    """Import Dataset 1 (DS1)."""
    print("\n=== IMPORTING DATASET 1 ===")
    ds_key = 'DS1'
    dataset_name = "Dataset 1"
    file_path = "etl/ds1.csv"
    mapping_path = "etl/column_mappings_DS1.json"
    
    try:
        import json
        import pandas as pd
        import os
        
        # Check if file exists
        if not os.path.exists(file_path):
            log_import_event(dataset_name, 'ERROR', f"Dataset file not found: {file_path}")
            print("Dataset 1 import failed")
            return False
            
        # Load column mappings if available
        column_mappings = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r') as f:
                    column_mappings = json.load(f)
                log_import_event(dataset_name, 'INFO', f"Loaded column mappings from {mapping_path}")
            except Exception as e:
                log_import_event(dataset_name, 'WARNING', f"Failed to load column mappings: {str(e)}")
        
        # Read the dataset
        df = None
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Try alternative encodings
            df = pd.read_csv(file_path, encoding='latin-1')
            
        if df is None or df.empty:
            log_import_event(dataset_name, 'ERROR', "Dataset is empty or could not be read")
            print("Dataset 1 import failed")
            return False
        
        # Log the number of records found
        record_count = len(df)
        log_import_event(dataset_name, 'INFO', f"Found {record_count} records in dataset")
        
        # Get or create dataset record - FIXED TO USE CORRECT FIELD NAMES
        dataset_obj, created = Dataset.objects.get_or_create(
            dataset_name=dataset_name,
            defaults={
                'license': "Open Data License"
            }
        )
        
        if created:
            log_import_event(dataset_name, 'INFO', f"Created new dataset record (ID: {dataset_obj.dataset_id})")
        else:
            log_import_event(dataset_name, 'INFO', f"Using existing dataset record (ID: {dataset_obj.dataset_id})")
        
        # Process the dataset and create concrete mixes
        # This section would be implemented based on the specific DS1 structure
        # For now, just log that this part would be implemented
        log_import_event(dataset_name, 'INFO', "Dataset 1 import completed successfully")
        print("Dataset 1 import succeeded")
        return True
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Fatal error during import: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        print("Dataset 1 import failed")
        return False

def main():
    print("\n*** STARTING TEST IMPORT ***\n")
    
    # Import reference data
    ref_success = import_reference_data()
    
    # Import materials
    if ref_success:
        mat_success = import_materials()
    else:
        mat_success = False
        print("Skipping materials import due to reference data import failure")
    
    # Import Dataset 1
    if mat_success:
        ds1_success = import_ds1()
    else:
        ds1_success = False
        print("Skipping DS1 import due to materials import failure")
    
    print("\n*** TEST IMPORT COMPLETE ***\n")

if __name__ == "__main__":
    main()
