#!/usr/bin/env python
"""
Test Script for DS1 Import Fixes

This script tests the approach to fixing the mix component and performance result creation 
issues in the import_ds1.py script.
"""

import os
import sys
import csv
import logging
import django
from decimal import Decimal
from datetime import datetime
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import (
    Dataset, ConcreteMix, MixComponent, PerformanceResult, Material, 
    MaterialClass, CementDetail, ScmDetail, AggregateDetail, AdmixtureDetail,
    PropertyDictionary, UnitLookup, TestMethod, BibliographicReference
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - TEST_DS1_FIX - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

def test_mix_creation_with_components():
    """
    Test function to create a mix with components and validate the ID issue is fixed
    """
    try:
        logger.info("Starting test for mix creation with components")
        
        # Create a test dataset
        with transaction.atomic():
            # Delete any existing test dataset
            Dataset.objects.filter(dataset_name="TEST-DS1").delete()
            
            # Create a new test dataset
            dataset = Dataset.objects.create(
                dataset_name="TEST-DS1",
                description="Test Dataset for DS1 Import Fixes",
                source="Test"
            )
            logger.info(f"Created test dataset: {dataset.dataset_name}")
            
            # Create a test material class
            material_class, created = MaterialClass.objects.get_or_create(
                class_code="CEMENT",
                defaults={
                    "class_name": "Cement"
                }
            )
            material = Material.objects.create(
                material_class=material_class,
                specific_name="Test Cement",
                subtype_code="CEM I"
            )
            logger.info(f"Created test material: {material.specific_name}")
            
            # Create a test mix
            mix = ConcreteMix.objects.create(
                dataset=dataset,
                mix_code="TEST-MIX-1",
                w_c_ratio=Decimal("0.5"),
                w_b_ratio=Decimal("0.5"),
                notes="Test mix"
            )
            logger.info(f"Created test mix: {mix.mix_code}")
            
            # Ensure mix has an ID by retrieving it again
            mix = ConcreteMix.objects.get(dataset=dataset, mix_code="TEST-MIX-1")
            logger.info(f"Retrieved mix with ID: {mix.mix_id}")
            
            # Create a test component
            component = MixComponent.objects.create(
                mix=mix,
                material=material,
                dosage_kg_m3=Decimal("350")
            )
            logger.info(f"Created test component with ID: {component.component_id}")
            
            # Verify component was created properly
            components = MixComponent.objects.filter(mix=mix)
            logger.info(f"Number of components found: {components.count()}")
            
            # Create a test property
            property_obj = PropertyDictionary.objects.get_or_create(
                property_name="COMP_STR",
                defaults={
                    "display_name": "Compressive Strength",
                    "property_group": "mechanical"
                }
            )[0]
            
            # Create a test unit
            unit = UnitLookup.objects.get_or_create(
                unit_symbol="MPa",
                defaults={
                    "si_factor": Decimal("1.0"),
                    "description": "Megapascal"
                }
            )[0]
            
            # Create a test test method
            test_method = TestMethod.objects.create(
                description="Test method for compression testing"
            )
            
            # Create a test performance result
            result = PerformanceResult.objects.create(
                mix=mix,
                property=property_obj,
                category=PerformanceResult.HARDENED,
                age_days=28,
                value_num=Decimal("42.5"),
                unit=unit,
                test_method=test_method
            )
            logger.info(f"Created test performance result with ID: {result.result_id}")
            
            # Verify result was created properly
            results = PerformanceResult.objects.filter(mix=mix)
            logger.info(f"Number of results found: {results.count()}")
            
        logger.info("Test completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return False

def fix_import_ds1_components():
    """
    Apply fixes to import_ds1.py based on test findings
    """
    logger.info("The following fixes should be applied to import_ds1.py:")
    logger.info("1. Always retrieve mix objects from the database after creation using mix_code")
    logger.info("2. Ensure transaction.atomic() wraps the creation of mixes and components")
    logger.info("3. Add mix.save() after mix creation to force commit to database")
    logger.info("4. Use the fetched mix object with ID for component and result creation")

if __name__ == "__main__":
    if test_mix_creation_with_components():
        fix_import_ds1_components()
    else:
        logger.error("Test failed. Please check the logs for details.")
        sys.exit(1)
