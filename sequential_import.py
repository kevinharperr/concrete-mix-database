import os
import django
import sys
import time
import csv
import json
import logging
import pandas as pd
import numpy as np
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
import traceback

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f'import_{log_timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Import RefreshLogEntry after Django setup
from refresh_status.models import RefreshLogEntry

def log_import_event(dataset_name, event_type, message, data=None):
    """
    Log import events to both the RefreshLogEntry model and standard logging.
    
    Args:
        dataset_name (str): The name of the dataset being processed
        event_type (str): Type of event (INFO, WARNING, ERROR)
        message (str): The event message
        data (dict, optional): Additional details as JSON
    """
    # Standard logging
    if event_type == 'ERROR':
        logging.error(f"{dataset_name}: {message}")
        is_error = True
    elif event_type == 'WARNING':
        logging.warning(f"{dataset_name}: {message}")
        is_error = False
    else:  # INFO
        logging.info(f"{dataset_name}: {message}")
        is_error = False
    
    # Database logging
    try:
        RefreshLogEntry.objects.create(
            phase='Data Import',
            step=dataset_name,
            status=event_type,
            message=message,
            is_error=is_error,
            details=data
        )
    except Exception as e:
        logging.error(f"Failed to log event to database: {str(e)}")

logger = logging.getLogger(__name__)

# Import models from both cdb_app and refresh_status
from django.db import models, transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone

# Import all needed models
from cdb_app.models import (
    MaterialClass, Material, Dataset, ConcreteMix, MixComponent,
    UnitLookup, PropertyDictionary, CuringRegime, Standard,
    TestMethod, Specimen, PerformanceResult, MaterialProperty,
    CementDetail, ScmDetail, AggregateDetail, AggregateConstituent,
    AdmixtureDetail, FibreDetail
)
from refresh_status.models import DatabaseStatus, RefreshLogEntry

# Define datasets and their source files
DATASETS_CONFIG = {
    'DS1': {
        'name': 'Dataset 1',
        'file_path': 'etl/ds1.csv',
        'description': 'Base concrete mix dataset',
        'mappings': 'etl/column_mappings_DS1.json'
    },
    'DS2': {
        'name': 'Dataset 2',
        'file_path': 'etl/ds2.csv',
        'description': 'Experimental concrete mixes with SCMs',
        'mappings': 'etl/column_mappings_DS2.json'
    },
    'DS3': {
        'name': 'Dataset 3',
        'file_path': 'etl/ds3.csv',
        'description': 'High-performance concrete mixes',
        'mappings': 'etl/column_mappings_DS3.json'
    },
    'DS4': {
        'name': 'Dataset 4',
        'file_path': 'etl/ds4.csv',
        'description': 'Sustainable concrete formulations',
        'mappings': 'etl/column_mappings_DS4.json'
    },
    'DS5': {
        'name': 'Dataset 5',
        'file_path': 'etl/ds5.csv',
        'description': 'Fiber-reinforced concrete mixes',
        'mappings': 'etl/column_mappings_DS5.json'
    },
    'DS6': {
        'name': 'Dataset 6',
        'file_path': 'etl/ds6.csv',
        'description': 'Special application concrete',
        'mappings': 'etl/column_mappings_DS6.json'
    },
}

# Define import order based on dependencies
IMPORT_ORDER = [
    {
        'name': 'Reference Data', 
        'function': 'import_reference_data',
        'description': 'Material classes, units, and other lookup tables'
    },
    {
        'name': 'Materials',
        'function': 'import_materials',
        'description': 'All materials used in concrete mixes'
    }
]

# Add datasets in order
for ds_key, ds_config in DATASETS_CONFIG.items():
    IMPORT_ORDER.append({
        'name': ds_config['name'],
        'function': f'import_{ds_key.lower()}',
        'description': ds_config['description'],
        'config': ds_config
    })

# Common column mapping patterns across datasets
COMMON_COLUMN_PATTERNS = {
    # Material patterns
    'cement': ['cement', 'cem', 'opc', 'portland', 'cementitious'],
    'fly_ash': ['fly ash', 'flyash', 'fa', 'pfa'],
    'ggbs': ['slag', 'ggbs', 'ggbfs', 'ground granulated', 'blast furnace'],
    'silica_fume': ['silica fume', 'silicafume', 'sf', 'microsilica', 'micro silica'],
    'metakaolin': ['metakaolin', 'mk'],
    'fine_aggregate': ['sand', 'fine agg', 'fine aggregate'],
    'coarse_aggregate': ['gravel', 'coarse agg', 'coarse aggregate', 'stone'],
    
    # Property patterns
    'water_cement_ratio': ['w/c', 'water cement', 'w/c ratio', 'water-cement ratio'],
    'water_binder_ratio': ['w/b', 'water binder', 'w/b ratio', 'water-binder ratio'],
    'compressive_strength': ['comp strength', 'compressive', 'fck', 'f\'c', 'strength'],
}

# Utility functions for data processing and validation
# This function is now defined at the top of the file
# def log_import_event(dataset_name, event_type, message, data=None):
#     """Log an import event to both the logger and the database."""
#     pass

def update_status(phase, progress, message=None):
    """Update the database status for tracking progress."""
    try:
        status = DatabaseStatus.objects.first()
        if not status:
            status = DatabaseStatus.objects.create()
        
        status.current_phase = phase
        status.progress_percent = progress
        if message:
            status.status_message = message
        status.save()
        
        logger.info(f"Status updated: Phase {phase}, Progress {progress}%, Message: {message}")
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        
def smart_column_mapping(df, target_columns, dataset_name):
    """Map columns from dataset to standard column names using pattern matching.
    
    Args:
        df: DataFrame with original dataset columns
        target_columns: List of standard column names to map to
        dataset_name: Name of dataset for logging
        
    Returns:
        Dictionary mapping standard column names to actual dataset column names
    """
    column_map = {}
    available_columns = set(df.columns)
    found_columns = set()
    
    # First try exact matches
    for target in target_columns:
        if target in available_columns:
            column_map[target] = target
            found_columns.add(target)
            
    # Then try case-insensitive matches
    for target in [t for t in target_columns if t not in column_map]:
        for col in [c for c in available_columns if c not in found_columns]:
            if target.lower() == col.lower():
                column_map[target] = col
                found_columns.add(col)
                break
                
    # Then try pattern matches from common patterns dictionary
    for target in [t for t in target_columns if t not in column_map]:
        if target in COMMON_COLUMN_PATTERNS:
            patterns = COMMON_COLUMN_PATTERNS[target]
            for pattern in patterns:
                for col in [c for c in available_columns if c not in found_columns]:
                    if pattern.lower() in col.lower():
                        column_map[target] = col
                        found_columns.add(col)
                        log_import_event(
                            dataset_name, 
                            'INFO', 
                            f"Mapped '{target}' to column '{col}' based on pattern '{pattern}'"
                        )
                        break
                if target in column_map:
                    break
    
    # Log missing columns
    missing = set(target_columns) - set(column_map.keys())
    if missing:
        log_import_event(
            dataset_name,
            'WARNING',
            f"Could not map {len(missing)} columns: {', '.join(missing)}"
        )
        
    return column_map

def safe_convert_value(value, target_type, default=None):
    """Safely convert a value to a target type with error handling.
    
    Args:
        value: The value to convert
        target_type: Target type ('int', 'float', 'decimal', 'bool', 'date')
        default: Default value if conversion fails
        
    Returns:
        Converted value or default
    """
    if pd.isna(value) or value is None or value == '':
        return default
        
    try:
        if target_type == 'int':
            return int(float(value))
        elif target_type == 'float':
            return float(value)
        elif target_type == 'decimal':
            if isinstance(value, str):
                # Remove any non-numeric chars except for decimal points
                clean_value = re.sub(r'[^\d.]', '', value)
                return Decimal(clean_value) if clean_value else default
            return Decimal(str(value))
        elif target_type == 'bool':
            if isinstance(value, str):
                return value.lower() in ['yes', 'y', 'true', 't', '1']
            return bool(value)
        elif target_type == 'date':
            if isinstance(value, str):
                # Try multiple date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
            return default
        else:
            return value
    except (ValueError, InvalidOperation, TypeError) as e:
        return default

def get_or_create_material(material_type, name, material_class_name, **properties):
    """Get or create a material with the given properties.
    
    Args:
        material_type: Type of material (cement, aggregate, etc.)
        name: Name of the material
        material_class_name: Name of the material class
        **properties: Additional properties to set
        
    Returns:
        Material instance
    """
    try:
        # Get or create material class
        material_class, _ = MaterialClass.objects.get_or_create(
            name=material_class_name,
            defaults={'description': f"Auto-created during import: {material_class_name}"}
        )
        
        # Try to find existing material
        material = Material.objects.filter(
            name__iexact=name,
            material_class=material_class
        ).first()
        
        if not material:
            # Create new material
            material = Material.objects.create(
                name=name,
                material_class=material_class,
                **properties
            )
            logger.info(f"Created new material: {name} ({material_class_name})")
        else:
            # Update material properties if they don't exist
            updated = False
            for key, value in properties.items():
                if getattr(material, key) is None and value is not None:
                    setattr(material, key, value)
                    updated = True
            if updated:
                material.save()
                logger.info(f"Updated material: {name} with new properties")
        
        return material
    except Exception as e:
        logger.error(f"Error creating/updating material {name}: {e}")
        return None

# Define import functions
def import_reference_data():
    """Import reference data like material classes, units, etc."""
    logger.info("Starting import of reference data...")
    dataset_name = "Reference Data"
    
    try:
        with transaction.atomic():
            # 1. Material Classes
            material_classes = [
                {'name': 'Cement', 'description': 'Binding materials including Portland cement and blended cements'},
                {'name': 'SCM', 'description': 'Supplementary cementitious materials like fly ash, GGBS, silica fume, etc.'},
                {'name': 'Aggregate', 'description': 'Coarse and fine aggregates used in concrete mixes'},
                {'name': 'Water', 'description': 'Mixing water for concrete'},
                {'name': 'Admixture', 'description': 'Chemical additives to modify concrete properties'},
                {'name': 'Fiber', 'description': 'Reinforcing fibers for concrete'},
            ]
            
            for mc_data in material_classes:
                # Ensure class_code is not longer than 8 characters
                class_code = mc_data['name'].upper()
                if len(class_code) > 8:
                    class_code = class_code[:8]
                
                obj, created = MaterialClass.objects.get_or_create(
                    class_name=mc_data['name'],
                    defaults={'class_code': class_code}
                )
                if created:
                    log_import_event(
                        dataset_name, 
                        'INFO', 
                        f"Created material class: {mc_data['name']}"
                    )
            
            # 2. Units
            units = [
                {'name': 'kg', 'description': 'Kilograms', 'conversion_factor': Decimal('1.0')},
                {'name': 'g', 'description': 'Grams', 'conversion_factor': Decimal('0.001')},
                {'name': 't', 'description': 'Metric tons', 'conversion_factor': Decimal('1000.0')},
                {'name': 'L', 'description': 'Liters', 'conversion_factor': Decimal('1.0')},
                {'name': 'mL', 'description': 'Milliliters', 'conversion_factor': Decimal('0.001')},
                {'name': 'm³', 'description': 'Cubic meters', 'conversion_factor': Decimal('1.0')},
                {'name': 'MPa', 'description': 'Megapascals', 'conversion_factor': Decimal('1.0')},
                {'name': 'GPa', 'description': 'Gigapascals', 'conversion_factor': Decimal('1000.0')},
                {'name': '%', 'description': 'Percentage', 'conversion_factor': Decimal('1.0')},
                {'name': 'mm', 'description': 'Millimeters', 'conversion_factor': Decimal('1.0')},
            ]
            
            for unit_data in units:
                obj, created = UnitLookup.objects.get_or_create(
                    unit_symbol=unit_data['name'],
                    defaults={
                        'description': unit_data['description'],
                        'si_factor': unit_data['conversion_factor']
                    }
                )
                if created:
                    log_import_event(
                        dataset_name, 
                        'INFO', 
                        f"Created unit: {unit_data['name']}"
                    )
            
            # 3. Property Dictionary
            properties = [
                {'property_name': 'density', 'display_name': 'Material density', 'property_group': 'physical', 'default_unit': 'kg/m³'},
                {'property_name': 'water_content', 'display_name': 'Water content in mix', 'property_group': 'physical', 'default_unit': 'kg/m³'},
                {'property_name': 'cement_content', 'display_name': 'Cement content in mix', 'property_group': 'physical', 'default_unit': 'kg/m³'},
                {'property_name': 'compressive_strength', 'display_name': 'Compressive strength of concrete', 'property_group': 'mechanical', 'default_unit': 'MPa'},
                {'property_name': 'water_cement_ratio', 'display_name': 'Water to cement ratio', 'property_group': 'physical', 'default_unit': None},
                {'property_name': 'water_binder_ratio', 'display_name': 'Water to binder ratio', 'property_group': 'physical', 'default_unit': None},
                {'property_name': 'slump', 'display_name': 'Concrete slump', 'property_group': 'physical', 'default_unit': 'mm'},
                {'property_name': 'air_content', 'display_name': 'Air content in concrete', 'property_group': 'physical', 'default_unit': '%'},
            ]
            
            for prop_data in properties:
                # Get the unit object if specified
                default_unit = None
                if prop_data['default_unit']:
                    try:
                        default_unit = UnitLookup.objects.get(unit_symbol=prop_data['default_unit'])
                    except UnitLookup.DoesNotExist:
                        logger.warning(f"Unit {prop_data['default_unit']} not found for property {prop_data['property_name']}")
                
                obj, created = PropertyDictionary.objects.get_or_create(
                    property_name=prop_data['property_name'],
                    defaults={
                        'display_name': prop_data['display_name'],
                        'property_group': prop_data['property_group'],
                        'default_unit': default_unit
                    }
                )
                if created:
                    log_import_event(
                        dataset_name, 
                        'INFO', 
                        f"Created property: {prop_data['property_name']}"
                    )
            
            # 4. Testing Standards
            standards = [
                {'code': 'ASTM C39', 'title': 'Standard Test Method for Compressive Strength'},
                {'code': 'EN 12390-3', 'title': 'European Standard for Compressive Strength'},
                {'code': 'ASTM C143', 'title': 'Standard Test Method for Slump'},
                {'code': 'ASTM C231', 'title': 'Standard Test Method for Air Content'},
            ]
            
            for std_data in standards:
                obj, created = Standard.objects.get_or_create(
                    code=std_data['code'],
                    defaults={'title': std_data['title']}
                )
                if created:
                    log_import_event(
                        dataset_name, 
                        'INFO', 
                        f"Created standard: {std_data['code']}"
                    )
                
        log_import_event(
            dataset_name, 
            'INFO', 
            "Reference data import completed successfully"
        )
        return True
    except Exception as e:
        log_import_event(
            dataset_name, 
            'ERROR', 
            f"Error importing reference data: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        return False

def import_materials():
    """Import common materials used across multiple datasets.
    
    This function creates baseline materials that will be referenced by the concrete mixes.
    """
    logger.info("Starting import of materials...")
    dataset_name = "Common Materials"
    
    try:
        with transaction.atomic():
            # Get material classes
            cement_class = MaterialClass.objects.get(class_name='Cement')
            scm_class = MaterialClass.objects.get(class_name='SCM')
            aggregate_class = MaterialClass.objects.get(class_name='Aggregate')
            water_class = MaterialClass.objects.get(class_name='Water')
            admixture_class = MaterialClass.objects.get(class_name='Admixture')
            fiber_class = MaterialClass.objects.get(class_name='Fiber')
            
            # 1. Create common cement types
            cements = [
                {'name': 'Ordinary Portland Cement (CEM I)', 'code': 'OPC', 'material_class': cement_class},
                {'name': 'CEM II/A-L', 'code': 'CEM2A-L', 'material_class': cement_class},
                {'name': 'CEM II/B-V', 'code': 'CEM2B-V', 'material_class': cement_class},
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
            
            # 2. Create common SCMs
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
            
            # 3. Create common aggregate types
            aggregates = [
                {'name': 'Fine Aggregate (0-4mm)', 'code': 'FA-04', 'material_class': aggregate_class, 'is_fine': True},
                {'name': 'Coarse Aggregate (4-10mm)', 'code': 'CA-410', 'material_class': aggregate_class, 'is_fine': False},
                {'name': 'Coarse Aggregate (10-20mm)', 'code': 'CA-1020', 'material_class': aggregate_class, 'is_fine': False},
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
                    # Create aggregate details
                    # Parse size range from the name, e.g., '0-4mm', '4-10mm', '10-20mm'
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
            
            # 4. Create water
            water, created = Material.objects.get_or_create(
                specific_name='Mixing Water',
                material_class=water_class,
                defaults={
                    'subtype_code': 'WATER',
                }
            )
            
            if created:
                log_import_event(
                    dataset_name,
                    'INFO',
                    "Created water material"
                )
            
            # 5. Create common admixture types
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
        return True
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Error importing materials: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        return False

def import_ds1():
    """Import Dataset 1 (DS1).
    
    This function handles the import of the first dataset, which contains the base concrete mixes.
    It includes validation, data normalization and proper error handling.
    """
    ds_key = 'DS1'
    dataset_name = DATASETS_CONFIG[ds_key]['name']
    file_path = DATASETS_CONFIG[ds_key]['file_path']
    mapping_path = DATASETS_CONFIG[ds_key]['mappings']
    
    logger.info(f"Starting import of {dataset_name}...")
    log_import_event(dataset_name, 'INFO', f"Beginning import process from {file_path}")
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            log_import_event(
                dataset_name, 
                'ERROR', 
                f"Dataset file not found: {file_path}"
            )
            return False
            
        # Load column mappings if available
        column_mappings = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r') as f:
                    column_mappings = json.load(f)
                log_import_event(
                    dataset_name,
                    'INFO',
                    f"Loaded column mappings from {mapping_path}"
                )
            except Exception as e:
                log_import_event(
                    dataset_name,
                    'WARNING',
                    f"Failed to load column mappings: {str(e)}"
                )
        
        # Read the dataset
        df = None
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Try alternative encodings
            df = pd.read_csv(file_path, encoding='latin-1')
            
        if df is None or df.empty:
            log_import_event(
                dataset_name,
                'ERROR',
                "Dataset is empty or could not be read"
            )
            return False
        
        # Log the number of records found
        record_count = len(df)
        log_import_event(
            dataset_name,
            'INFO',
            f"Found {record_count} records in dataset"
        )
        
        # Get or create dataset record
        dataset_obj, created = Dataset.objects.get_or_create(
            name=dataset_name,
            defaults={
                'description': DATASETS_CONFIG[ds_key]['description'],
                'source_file': file_path,
                'import_date': timezone.now().date()
            }
        )
        
        if not created:
            # Update the existing dataset record
            dataset_obj.import_date = timezone.now().date()
            dataset_obj.save()
            log_import_event(
                dataset_name,
                'INFO',
                f"Updated existing dataset record (ID: {dataset_obj.id})"
            )
        else:
            log_import_event(
                dataset_name,
                'INFO',
                f"Created new dataset record (ID: {dataset_obj.id})"
            )
        
        # Map column names using smart mapping or predefined mappings
        required_columns = [
            'mix_code', 'mix_name', 'cement_content', 'water_content', 
            'water_cement_ratio', 'fine_aggregate', 'coarse_aggregate'
        ]
        
        # Use either provided mappings or smart column mapping
        if column_mappings:
            # Use provided mappings
            mapped_columns = {}
            for target_col in required_columns:
                if target_col in column_mappings:
                    mapped_columns[target_col] = column_mappings[target_col]
                else:
                    # Try direct match as fallback
                    if target_col in df.columns:
                        mapped_columns[target_col] = target_col
        else:
            # Use smart column mapping
            mapped_columns = smart_column_mapping(df, required_columns, dataset_name)
        
        # Validate that we have the minimum required columns mapped
        critical_columns = ['mix_code', 'cement_content', 'water_content']
        missing_critical = [col for col in critical_columns if col not in mapped_columns]
        
        if missing_critical:
            log_import_event(
                dataset_name,
                'ERROR',
                f"Missing critical columns: {', '.join(missing_critical)}"
            )
            return False
            
        # Process each mix in the dataset
        successful_imports = 0
        failed_imports = 0
        
        # Transaction is used for the entire import to ensure consistency
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Generate a mix code if not present or mapped
                    mix_code = None
                    if 'mix_code' in mapped_columns:
                        mix_code = row[mapped_columns['mix_code']]
                    
                    if pd.isna(mix_code) or not mix_code:
                        mix_code = f"DS1-{index+1}"
                    
                    # Generate mix name if not present or mapped
                    mix_name = None
                    if 'mix_name' in mapped_columns:
                        mix_name = row[mapped_columns['mix_name']]
                    
                    if pd.isna(mix_name) or not mix_name:
                        mix_name = f"Mix {mix_code}"
                        
                    # Get the cement content
                    cement_content = None
                    if 'cement_content' in mapped_columns:
                        cement_content = safe_convert_value(
                            row[mapped_columns['cement_content']], 
                            'decimal', 
                            None
                        )
                    
                    if cement_content is None:
                        log_import_event(
                            dataset_name,
                            'ERROR',
                            f"Mix {mix_code}: Missing cement content"
                        )
                        failed_imports += 1
                        continue
                    
                    # Get the water content
                    water_content = None
                    if 'water_content' in mapped_columns:
                        water_content = safe_convert_value(
                            row[mapped_columns['water_content']], 
                            'decimal', 
                            None
                        )
                    
                    if water_content is None:
                        log_import_event(
                            dataset_name,
                            'ERROR',
                            f"Mix {mix_code}: Missing water content"
                        )
                        failed_imports += 1
                        continue
                    
                    # Calculate or get water-cement ratio
                    w_c_ratio = None
                    if 'water_cement_ratio' in mapped_columns:
                        w_c_ratio = safe_convert_value(
                            row[mapped_columns['water_cement_ratio']],
                            'decimal',
                            None
                        )
                    
                    # If w/c ratio not available, calculate it
                    if w_c_ratio is None and cement_content > 0:
                        w_c_ratio = Decimal(water_content) / Decimal(cement_content)
                    
                    # Create or update the mix
                    mix, created = ConcreteMix.objects.get_or_create(
                        code=mix_code,
                        dataset=dataset_obj,
                        defaults={
                            'name': mix_name,
                            'water_cement_ratio': w_c_ratio,
                            'water_binder_ratio': w_c_ratio,  # Assume same as w/c for now
                            'description': f"Imported from {dataset_name}"
                        }
                    )
                    
                    if not created:
                        # Update existing mix
                        mix.name = mix_name
                        mix.water_cement_ratio = w_c_ratio
                        mix.water_binder_ratio = w_c_ratio  # Update this if SCMs present
                        mix.save()
                        
                        # Delete existing components to recreate them
                        MixComponent.objects.filter(concrete_mix=mix).delete()
                    
                    # Add cement component
                    cement_material = Material.objects.get(name='Ordinary Portland Cement (CEM I)')
                    MixComponent.objects.create(
                        concrete_mix=mix,
                        material=cement_material,
                        quantity=cement_content,
                        unit='kg/m³'
                    )
                    
                    # Add water component
                    water_material = Material.objects.get(name='Mixing Water')
                    MixComponent.objects.create(
                        concrete_mix=mix,
                        material=water_material,
                        quantity=water_content,
                        unit='kg/m³'
                    )
                    
                    # Add fine aggregate if available
                    if 'fine_aggregate' in mapped_columns:
                        fine_agg_content = safe_convert_value(
                            row[mapped_columns['fine_aggregate']],
                            'decimal',
                            None
                        )
                        
                        if fine_agg_content is not None and fine_agg_content > 0:
                            fine_agg_material = Material.objects.get(name='Fine Aggregate (0-4mm)')
                            MixComponent.objects.create(
                                concrete_mix=mix,
                                material=fine_agg_material,
                                quantity=fine_agg_content,
                                unit='kg/m³'
                            )
                    
                    # Add coarse aggregate if available
                    if 'coarse_aggregate' in mapped_columns:
                        coarse_agg_content = safe_convert_value(
                            row[mapped_columns['coarse_aggregate']],
                            'decimal',
                            None
                        )
                        
                        if coarse_agg_content is not None and coarse_agg_content > 0:
                            coarse_agg_material = Material.objects.get(name='Coarse Aggregate (10-20mm)')
                            MixComponent.objects.create(
                                concrete_mix=mix,
                                material=coarse_agg_material,
                                quantity=coarse_agg_content,
                                unit='kg/m³'
                            )
                    
                    successful_imports += 1
                    
                except Exception as e:
                    log_import_event(
                        dataset_name,
                        'ERROR',
                        f"Error importing mix at row {index+1}: {str(e)}",
                        data={'traceback': traceback.format_exc()}
                    )
                    failed_imports += 1
        
        # Log summary
        log_import_event(
            dataset_name,
            'INFO',
            f"Import completed: {successful_imports} mixes imported successfully, {failed_imports} failed"
        )
        
        return successful_imports > 0  # Consider successful if at least one mix was imported
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Fatal error during import: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        return False

def import_ds2():
    """Import Dataset 2 (DS2).
    
    This function handles the import of the second dataset, which contains experimental mixes with SCMs.
    It specifically addresses the known issues with DS2:
    - Mix code misalignment
    - Missing components (especially aggregates)
    - Incorrect water-binder ratios
    - Incomplete material properties
    """
    ds_key = 'DS2'
    dataset_name = DATASETS_CONFIG[ds_key]['name']
    file_path = DATASETS_CONFIG[ds_key]['file_path']
    mapping_path = DATASETS_CONFIG[ds_key]['mappings']
    
    logger.info(f"Starting import of {dataset_name}...")
    log_import_event(dataset_name, 'INFO', f"Beginning import process from {file_path}")
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            log_import_event(
                dataset_name, 
                'ERROR', 
                f"Dataset file not found: {file_path}"
            )
            return False
            
        # Load column mappings if available
        column_mappings = {}
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r') as f:
                    column_mappings = json.load(f)
                log_import_event(
                    dataset_name,
                    'INFO',
                    f"Loaded column mappings from {mapping_path}"
                )
            except Exception as e:
                log_import_event(
                    dataset_name,
                    'WARNING',
                    f"Failed to load column mappings: {str(e)}"
                )
        
        # Read the dataset
        df = None
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Try alternative encodings
            df = pd.read_csv(file_path, encoding='latin-1')
            
        if df is None or df.empty:
            log_import_event(
                dataset_name,
                'ERROR',
                "Dataset is empty or could not be read"
            )
            return False
        
        # Log the number of records found
        record_count = len(df)
        log_import_event(
            dataset_name,
            'INFO',
            f"Found {record_count} records in dataset"
        )
        
        # Get or create dataset record
        dataset_obj, created = Dataset.objects.get_or_create(
            name=dataset_name,
            defaults={
                'description': DATASETS_CONFIG[ds_key]['description'],
                'source_file': file_path,
                'import_date': timezone.now().date()
            }
        )
        
        if not created:
            # Update the existing dataset record
            dataset_obj.import_date = timezone.now().date()
            dataset_obj.save()
            log_import_event(
                dataset_name,
                'INFO',
                f"Updated existing dataset record (ID: {dataset_obj.id})"
            )
        else:
            log_import_event(
                dataset_name,
                'INFO',
                f"Created new dataset record (ID: {dataset_obj.id})"
            )
        
        # Map column names using smart mapping or predefined mappings
        required_columns = [
            'mix_code', 'mix_name', 'cement_content', 'water_content', 
            'water_cement_ratio', 'fine_aggregate', 'coarse_aggregate',
            'fly_ash_content', 'ggbs_content', 'silica_fume_content',
            'admixture_content', 'compressive_strength'
        ]
        
        # Use either provided mappings or smart column mapping
        if column_mappings:
            # Use provided mappings
            mapped_columns = {}
            for target_col in required_columns:
                if target_col in column_mappings:
                    mapped_columns[target_col] = column_mappings[target_col]
                else:
                    # Try direct match as fallback
                    if target_col in df.columns:
                        mapped_columns[target_col] = target_col
        else:
            # Use smart column mapping
            mapped_columns = smart_column_mapping(df, required_columns, dataset_name)
        
        # Validate that we have the minimum required columns mapped
        critical_columns = ['mix_code', 'cement_content', 'water_content']
        missing_critical = [col for col in critical_columns if col not in mapped_columns]
        
        if missing_critical:
            log_import_event(
                dataset_name,
                'ERROR',
                f"Missing critical columns: {', '.join(missing_critical)}"
            )
            return False
            
        # Process each mix in the dataset
        successful_imports = 0
        failed_imports = 0
        
        # Transaction is used for the entire dataset import to ensure consistency
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Generate a mix code if not present or mapped
                    # Known issue: Mix code misalignment in DS2
                    mix_code = None
                    if 'mix_code' in mapped_columns:
                        mix_code = row[mapped_columns['mix_code']]
                    
                    if pd.isna(mix_code) or not mix_code:
                        # Generate a consistent code based on row index
                        mix_code = f"DS2-{index+1:03d}"  # Use padding for consistent sorting
                    else:
                        # Clean up mix code and ensure consistency
                        # Strip any non-alphanumeric characters except dash
                        mix_code = re.sub(r'[^a-zA-Z0-9-]', '', str(mix_code))
                        if not mix_code.startswith('DS2-'):
                            mix_code = f"DS2-{mix_code}"
                    
                    # Generate mix name if not present or mapped
                    mix_name = None
                    if 'mix_name' in mapped_columns:
                        mix_name = row[mapped_columns['mix_name']]
                    
                    if pd.isna(mix_name) or not mix_name:
                        mix_name = f"Mix {mix_code}"
                        
                    # Get the cement content
                    cement_content = None
                    if 'cement_content' in mapped_columns:
                        cement_content = safe_convert_value(
                            row[mapped_columns['cement_content']], 
                            'decimal', 
                            None
                        )
                    
                    if cement_content is None:
                        log_import_event(
                            dataset_name,
                            'ERROR',
                            f"Mix {mix_code}: Missing cement content"
                        )
                        failed_imports += 1
                        continue
                    
                    # Get the water content
                    water_content = None
                    if 'water_content' in mapped_columns:
                        water_content = safe_convert_value(
                            row[mapped_columns['water_content']], 
                            'decimal', 
                            None
                        )
                    
                    if water_content is None:
                        log_import_event(
                            dataset_name,
                            'ERROR',
                            f"Mix {mix_code}: Missing water content"
                        )
                        failed_imports += 1
                        continue
                    
                    # Get SCM contents
                    fly_ash_content = None
                    if 'fly_ash_content' in mapped_columns:
                        fly_ash_content = safe_convert_value(
                            row[mapped_columns['fly_ash_content']], 
                            'decimal', 
                            Decimal('0')
                        )
                        
                    ggbs_content = None
                    if 'ggbs_content' in mapped_columns:
                        ggbs_content = safe_convert_value(
                            row[mapped_columns['ggbs_content']], 
                            'decimal', 
                            Decimal('0')
                        )
                        
                    silica_fume_content = None
                    if 'silica_fume_content' in mapped_columns:
                        silica_fume_content = safe_convert_value(
                            row[mapped_columns['silica_fume_content']], 
                            'decimal', 
                            Decimal('0')
                        )
                    
                    # Calculate total binder content (cement + SCMs)
                    binder_content = cement_content
                    if fly_ash_content:
                        binder_content += fly_ash_content
                    if ggbs_content:
                        binder_content += ggbs_content
                    if silica_fume_content:
                        binder_content += silica_fume_content
                    
                    # Calculate or get water-cement ratio
                    w_c_ratio = None
                    if 'water_cement_ratio' in mapped_columns:
                        w_c_ratio = safe_convert_value(
                            row[mapped_columns['water_cement_ratio']],
                            'decimal',
                            None
                        )
                    
                    # If w/c ratio not available, calculate it
                    if w_c_ratio is None and cement_content > 0:
                        w_c_ratio = Decimal(water_content) / Decimal(cement_content)
                    
                    # Calculate water-binder ratio
                    # Known issue: Incorrect water-binder ratios in DS2
                    w_b_ratio = None
                    if binder_content > 0:
                        w_b_ratio = Decimal(water_content) / Decimal(binder_content)
                    else:
                        w_b_ratio = w_c_ratio  # Default to w/c if no SCMs
                    
                    # Create or update the mix
                    mix, created = ConcreteMix.objects.get_or_create(
                        code=mix_code,
                        dataset=dataset_obj,
                        defaults={
                            'name': mix_name,
                            'water_cement_ratio': w_c_ratio,
                            'water_binder_ratio': w_b_ratio,
                            'description': f"Imported from {dataset_name}"
                        }
                    )
                    
                    if not created:
                        # Update existing mix
                        mix.name = mix_name
                        mix.water_cement_ratio = w_c_ratio
                        mix.water_binder_ratio = w_b_ratio
                        mix.save()
                        
                        # Delete existing components to recreate them
                        MixComponent.objects.filter(concrete_mix=mix).delete()
                    
                    # Add cement component
                    cement_material = Material.objects.get(name='Ordinary Portland Cement (CEM I)')
                    MixComponent.objects.create(
                        concrete_mix=mix,
                        material=cement_material,
                        quantity=cement_content,
                        unit='kg/m³'
                    )
                    
                    # Add water component
                    water_material = Material.objects.get(name='Mixing Water')
                    MixComponent.objects.create(
                        concrete_mix=mix,
                        material=water_material,
                        quantity=water_content,
                        unit='kg/m³'
                    )
                    
                    # Add SCM components
                    if fly_ash_content and fly_ash_content > 0:
                        fly_ash_material = Material.objects.get(name='Fly Ash')
                        MixComponent.objects.create(
                            concrete_mix=mix,
                            material=fly_ash_material,
                            quantity=fly_ash_content,
                            unit='kg/m³'
                        )
                        
                    if ggbs_content and ggbs_content > 0:
                        ggbs_material = Material.objects.get(name='GGBS')
                        MixComponent.objects.create(
                            concrete_mix=mix,
                            material=ggbs_material,
                            quantity=ggbs_content,
                            unit='kg/m³'
                        )
                        
                    if silica_fume_content and silica_fume_content > 0:
                        sf_material = Material.objects.get(name='Silica Fume')
                        MixComponent.objects.create(
                            concrete_mix=mix,
                            material=sf_material,
                            quantity=silica_fume_content,
                            unit='kg/m³'
                        )
                    
                    # Add fine aggregate if available
                    # Known issue: Missing components (especially aggregates) in DS2
                    if 'fine_aggregate' in mapped_columns:
                        fine_agg_content = safe_convert_value(
                            row[mapped_columns['fine_aggregate']],
                            'decimal',
                            None
                        )
                        
                        if fine_agg_content is not None and fine_agg_content > 0:
                            fine_agg_material = Material.objects.get(name='Fine Aggregate (0-4mm)')
                            MixComponent.objects.create(
                                concrete_mix=mix,
                                material=fine_agg_material,
                                quantity=fine_agg_content,
                                unit='kg/m³'
                            )
                        else:
                            # Log missing aggregate as warning
                            log_import_event(
                                dataset_name,
                                'WARNING',
                                f"Mix {mix_code}: Missing fine aggregate content"
                            )
                    
                    # Add coarse aggregate if available
                    if 'coarse_aggregate' in mapped_columns:
                        coarse_agg_content = safe_convert_value(
                            row[mapped_columns['coarse_aggregate']],
                            'decimal',
                            None
                        )
                        
                        if coarse_agg_content is not None and coarse_agg_content > 0:
                            coarse_agg_material = Material.objects.get(name='Coarse Aggregate (10-20mm)')
                            MixComponent.objects.create(
                                concrete_mix=mix,
                                material=coarse_agg_material,
                                quantity=coarse_agg_content,
                                unit='kg/m³'
                            )
                        else:
                            # Log missing aggregate as warning
                            log_import_event(
                                dataset_name,
                                'WARNING',
                                f"Mix {mix_code}: Missing coarse aggregate content"
                            )
                    
                    # Add admixture if available
                    if 'admixture_content' in mapped_columns:
                        admixture_content = safe_convert_value(
                            row[mapped_columns['admixture_content']],
                            'decimal',
                            None
                        )
                        
                        if admixture_content is not None and admixture_content > 0:
                            admixture_material = Material.objects.get(name='Superplasticizer')
                            MixComponent.objects.create(
                                concrete_mix=mix,
                                material=admixture_material,
                                quantity=admixture_content,
                                unit='kg/m³'
                            )
                    
                    # Store compressive strength if available
                    if 'compressive_strength' in mapped_columns:
                        comp_strength = safe_convert_value(
                            row[mapped_columns['compressive_strength']],
                            'decimal',
                            None
                        )
                        
                        if comp_strength is not None and comp_strength > 0:
                            # Create specimen and performance result
                            specimen = Specimen.objects.create(
                                concrete_mix=mix,
                                age_days=28,  # Default to 28 days if not specified
                                shape='cube',
                                dimensions='100x100x100',
                                curing_regime=None
                            )
                            
                            PerformanceResult.objects.create(
                                specimen=specimen,
                                property_name='compressive_strength',
                                value=comp_strength,
                                unit='MPa'
                            )
                    
                    successful_imports += 1
                    
                except Exception as e:
                    log_import_event(
                        dataset_name,
                        'ERROR',
                        f"Error importing mix at row {index+1}: {str(e)}",
                        data={'traceback': traceback.format_exc()}
                    )
                    failed_imports += 1
        
        # Log summary
        log_import_event(
            dataset_name,
            'INFO',
            f"Import completed: {successful_imports} mixes imported successfully, {failed_imports} failed"
        )
        
        return successful_imports > 0  # Consider successful if at least one mix was imported
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Fatal error during import: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        return False

def validate_import():
    """Run comprehensive validation across all datasets to ensure data integrity.
    
    This function performs various checks on the imported data to identify potential issues:
    1. Check for mixes without components
    2. Check for missing water-binder ratios
    3. Validate calculated water-binder ratios
    4. Check material usage and component consistency
    5. Verify performance results
    """
    dataset_name = "Validation"
    logger.info("Starting comprehensive validation of imported data...")
    
    try:
        # 1. Basic counts and statistics
        material_count = Material.objects.count()
        dataset_count = Dataset.objects.count()
        mix_count = Mix.objects.count()
        component_count = MixComponent.objects.count()
        specimen_count = Specimen.objects.count()
        result_count = PerformanceResult.objects.count()
        
        log_import_event(
            dataset_name,
            'INFO',
            f"Database summary:\n" +
            f"  - Datasets: {dataset_count}\n" +
            f"  - Materials: {material_count}\n" +
            f"  - Mixes: {mix_count}\n" +
            f"  - Mix Components: {component_count}\n" +
            f"  - Specimens: {specimen_count}\n" +
            f"  - Performance Results: {result_count}"
        )
        
        # 2. Check for mixes without components
        mixes_without_components = Mix.objects.filter(mixcomponent__isnull=True)
        if mixes_without_components.exists():
            mix_codes = [mix.code for mix in mixes_without_components[:10]]
            if len(mixes_without_components) > 10:
                mix_codes.append('...')
                
            log_import_event(
                dataset_name,
                'WARNING',
                f"Found {mixes_without_components.count()} mixes without any components!\n" +
                f"Example mix codes: {', '.join(mix_codes)}"
            )
            
        # 3. Check for missing critical components (cement and water)
        mixes_missing_cement = Mix.objects.exclude(
            mixcomponent__material__material_class__name='Cement'
        )
        
        if mixes_missing_cement.exists():
            log_import_event(
                dataset_name,
                'ERROR',
                f"Found {mixes_missing_cement.count()} mixes without cement component!"
            )
            
        mixes_missing_water = Mix.objects.exclude(
            mixcomponent__material__material_class__name='Water'
        )
        
        if mixes_missing_water.exists():
            log_import_event(
                dataset_name,
                'ERROR',
                f"Found {mixes_missing_water.count()} mixes without water component!"
            )
            
        # 4. Check for inconsistent water-binder ratios
        # This is a known issue in DS2 that we're specifically checking for
        mixes_with_scm = Mix.objects.filter(
            mixcomponent__material__material_class__name='SCM'
        ).distinct()
        
        inconsistent_wb_ratios = 0
        checked_mixes = 0
        
        for mix in mixes_with_scm.iterator():  # Use iterator for large querysets
            checked_mixes += 1
            
            # Get component quantities
            water_component = MixComponent.objects.filter(
                mix=mix,
                material__material_class__name='Water'
            ).first()
            
            if not water_component:
                continue
                
            cement_components = MixComponent.objects.filter(
                mix=mix,
                material__material_class__name='Cement'
            )
            
            scm_components = MixComponent.objects.filter(
                mix=mix,
                material__material_class__name='SCM'
            )
            
            # Calculate water-binder ratio
            water_content = water_component.quantity
            cement_content = sum(c.quantity for c in cement_components)
            scm_content = sum(c.quantity for c in scm_components)
            
            if cement_content + scm_content > 0:
                calculated_wb = Decimal(water_content) / Decimal(cement_content + scm_content)
                stored_wb = mix.water_binder_ratio
                
                # Allow for small rounding differences (0.01)
                if abs(calculated_wb - stored_wb) > Decimal('0.01'):
                    inconsistent_wb_ratios += 1
                    
                    # Update the incorrect ratio
                    mix.water_binder_ratio = calculated_wb
                    mix.save()
                    
                    log_import_event(
                        dataset_name,
                        'WARNING',
                        f"Fixed inconsistent water-binder ratio for mix {mix.code}: " +
                        f"Stored: {stored_wb}, Calculated: {calculated_wb:.3f}"
                    )
        
        if inconsistent_wb_ratios > 0:
            log_import_event(
                dataset_name,
                'WARNING',
                f"Fixed {inconsistent_wb_ratios} inconsistent water-binder ratios out of {checked_mixes} mixes with SCMs"
            )
        
        # 5. Check for mix components with unrealistic quantities
        unrealistic_components = MixComponent.objects.filter(
            quantity__gt=2000  # Unrealistically high for kg/m³
        )
        
        if unrealistic_components.exists():
            log_import_event(
                dataset_name,
                'WARNING',
                f"Found {unrealistic_components.count()} mix components with potentially unrealistic quantities (>2000 kg/m³)"
            )
        
        # 6. Verify performance results
        mixes_with_strength = Mix.objects.filter(
            specimen__performanceresult__property_name='compressive_strength'
        ).distinct().count()
        
        log_import_event(
            dataset_name,
            'INFO',
            f"Found {mixes_with_strength} mixes with compressive strength data"
        )
        
        # 7. Dataset-specific checks
        datasets = Dataset.objects.all()
        for dataset in datasets:
            mix_count = Mix.objects.filter(dataset=dataset).count()
            log_import_event(
                dataset_name,
                'INFO',
                f"Dataset '{dataset.name}' contains {mix_count} mixes"
            )
        
        # Return True if no critical errors were found
        validation_successful = not mixes_missing_cement.exists() and not mixes_missing_water.exists()
        
        if validation_successful:
            log_import_event(
                dataset_name,
                'INFO',
                "Validation completed successfully with no critical errors"
            )
        else:
            log_import_event(
                dataset_name,
                'ERROR',
                "Validation completed with critical errors that need to be addressed"
            )
            
        return validation_successful
        
    except Exception as e:
        log_import_event(
            dataset_name,
            'ERROR',
            f"Error during validation: {str(e)}",
            data={'traceback': traceback.format_exc()}
        )
        return False

def run_sequential_import():
    """Execute the full import sequence with proper error handling and logging.
    
    This function orchestrates the entire import process, running each step in sequence
    and providing detailed status updates and timing information.
    """
    start_time = time.time()
    logger.info("=== STARTING SEQUENTIAL IMPORT PROCESS ===\n")
    
    # Create a log entry for the start of the process
    log_import_event(
        "Sequential Import", 
        "INFO",
        f"Starting sequential import process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Initialize counters
    total_steps = len(IMPORT_ORDER) + 1  # +1 for validation
    current_step = 0
    step_times = {}
    
    # Update the database status
    update_status("Implementation", 0, "Starting import process")
    
    # Run each import step in sequence
    for import_step in IMPORT_ORDER:
        step_name = import_step['name']
        step_function = import_step['function']
        description = import_step.get('description', '')
        
        logger.info(f"\n*** IMPORTING {step_name} ({description}) ***")
        update_status("Implementation", (current_step / total_steps) * 100, f"Importing {step_name}")
        
        # Measure the time for each step
        step_start_time = time.time()
        
        try:
            # Get the function reference by name and call it
            import_func = globals()[step_function]
            success = import_func()
            
            step_elapsed = time.time() - step_start_time
            step_times[step_name] = step_elapsed
            
            if not success:
                logger.error(f"Failed to import {step_name}. Stopping import process.")
                update_status(
                    "Implementation", 
                    (current_step / total_steps) * 100, 
                    f"ERROR: Failed to import {step_name}"
                )
                
                log_import_event(
                    "Sequential Import", 
                    "ERROR",
                    f"Import process stopped due to failure in step: {step_name}"
                )
                return False
            
            current_step += 1
            logger.info(f"{step_name} import completed successfully in {step_elapsed:.2f} seconds")
            
            # Record timing information for performance optimization
            log_import_event(
                "Sequential Import", 
                "INFO",
                f"Step '{step_name}' completed in {step_elapsed:.2f} seconds"
            )
            
        except Exception as e:
            step_elapsed = time.time() - step_start_time
            logger.error(f"Unexpected error in {step_name} import: {e}")
            logger.error(traceback.format_exc())
            
            update_status(
                "Implementation", 
                (current_step / total_steps) * 100, 
                f"ERROR: Exception during {step_name} import"
            )
            
            log_import_event(
                "Sequential Import", 
                "ERROR",
                f"Exception during '{step_name}' import: {str(e)}",
                data={'traceback': traceback.format_exc()}
            )
            return False
    
    # Run validation
    logger.info("\n*** VALIDATING IMPORTED DATA ***")
    update_status("Implementation", (current_step / total_steps) * 100, "Validating imported data")
    
    validation_start = time.time()
    validation_success = validate_import()
    validation_elapsed = time.time() - validation_start
    
    step_times['Validation'] = validation_elapsed
    log_import_event(
        "Sequential Import", 
        "INFO",
        f"Validation completed in {validation_elapsed:.2f} seconds. Success: {validation_success}"
    )
    
    # Complete import process
    total_elapsed = time.time() - start_time
    
    logger.info(f"\n=== IMPORT PROCESS TIMING SUMMARY ===\n")
    for step, elapsed in step_times.items():
        percentage = (elapsed / total_elapsed) * 100
        logger.info(f"  - {step}: {elapsed:.2f} seconds ({percentage:.1f}%)")
    
    logger.info(f"\n=== IMPORT PROCESS COMPLETED IN {total_elapsed:.2f} SECONDS ===\n")
    
    # Final status update
    if validation_success:
        update_status("Implementation", 100, "Import process completed successfully")
        log_import_event(
            "Sequential Import", 
            "INFO",
            f"Import process completed successfully in {total_elapsed:.2f} seconds"
        )
    else:
        update_status("Implementation", 100, "Import completed with validation warnings")
        log_import_event(
            "Sequential Import", 
            "WARNING",
            f"Import process completed with validation issues in {total_elapsed:.2f} seconds"
        )
    
    return True

if __name__ == '__main__':
    confirm = input("Ready to start the sequential import process? (yes/no): ")
    if confirm.lower() == 'yes':
        run_sequential_import()
    else:
        print("Import process cancelled.")
