import os
import csv
import logging
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import models
from cdb_app.models import (
    Dataset, ConcreteMix, Material, MaterialClass, MixComponent, PropertyDictionary, 
    TestMethod, UnitLookup, PerformanceResult
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DS1_TEST')

# Constants
SOURCE_FILE = 'etl/ds1.csv'

def check_csv_file():
    """Check if the CSV file exists and contains valid data"""
    logger.info(f"Checking source file: {SOURCE_FILE}")
    try:
        with open(SOURCE_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            # Read the first row to get field names
            field_names = reader.fieldnames
            logger.info(f"CSV fields: {field_names}")
            
            # Read a few rows to check values
            rows = []
            for i, row in enumerate(reader):
                if i < 5:  # Only check first 5 rows
                    rows.append(row)
                else:
                    break
            
            for i, row in enumerate(rows):
                logger.info(f"Row {i+1}: cement_kg_m3={row.get('cement_kg_m3')}, water_kg_m3={row.get('water_kg_m3')}, testing_age={row.get('testing_age')}")
                
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")

def test_material_creation():
    """Test if materials can be created and retrieved properly"""
    try:
        # Create a test material class
        material_class, created = MaterialClass.objects.get_or_create(
            class_code='TEST',
            defaults={'class_name': 'Test Material Class'}
        )
        logger.info(f"Material class: {material_class.class_name} (created: {created})")
        
        # Create a test material
        material, created = Material.objects.get_or_create(
            material_class=material_class,
            specific_name='Test Material',
            defaults={'subtype_code': 'TEST'}
        )
        logger.info(f"Material: {material.specific_name} (created: {created})")
        
        # Get the first mix from the database
        try:
            mix = ConcreteMix.objects.first()
            logger.info(f"Found mix: {mix.mix_code}")
            
            # Try to create a mix component
            if mix and material:
                component = MixComponent.objects.create(
                    mix=mix,
                    material=material,
                    dosage_kg_m3=Decimal('100.0')
                )
                logger.info(f"Created test component: {component.id}")
        except Exception as e:
            logger.error(f"Error with mix component: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error testing material creation: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting DS1 import test")
    check_csv_file()
    test_material_creation()
    logger.info("Test completed")
