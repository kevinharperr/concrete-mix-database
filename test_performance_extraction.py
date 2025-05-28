#!/usr/bin/env python
# test_performance_extraction.py - Script to test and fix performance results extraction

import os
import sys
import logging
import django
import pandas as pd

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
django.setup()

from cdb_app.models import Standard, TestMethod, UnitLookup, MaterialClass, PropertyDictionary
from cdb_app.models import Dataset, ConcreteMix, PerformanceResult
from etl.test_dataset_importer import TestDatasetImporter

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_extraction')

def test_direct_extraction():
    """Test direct extraction of performance results from CSV data."""
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etl', 'test_dataset.csv')
    data = pd.read_csv(csv_path)
    
    logger.info(f"CSV data loaded with columns: {data.columns.tolist()}")
    logger.info(f"First row: {data.iloc[0].to_dict()}")
    
    # Get an existing mix for testing
    try:
        mix = ConcreteMix.objects.filter(mix_code__startswith='TM').first()
        if not mix:
            dataset, _ = Dataset.objects.get_or_create(
                dataset_name="TEST_DS",
                defaults={"license": "Test dataset for Database Refresh Plan"}
            )
            mix = ConcreteMix.objects.create(
                dataset=dataset,
                mix_code="TM_TEST",
                strength_class="C30/37",
                w_b_ratio=0.5
            )
            logger.info(f"Created test mix: {mix.mix_code}")
        else:
            logger.info(f"Using existing mix: {mix.mix_code}")
    except Exception as e:
        logger.error(f"Error getting/creating mix: {str(e)}")
        return
    
    # Create the results directly
    try:
        # Create test methods first if they don't exist
        comp_method, _ = TestMethod.objects.get_or_create(
            description="EN 12390-3 Compressive Test",
            defaults={"clause": ""}
        )
        slump_method, _ = TestMethod.objects.get_or_create(
            description="EN 12350-2 Slump Test",
            defaults={"clause": ""}
        )
        
        # Create units if they don't exist
        mpa_unit, _ = UnitLookup.objects.get_or_create(
            unit_symbol="MPa",
            defaults={"description": "Megapascals"}
        )
        mm_unit, _ = UnitLookup.objects.get_or_create(
            unit_symbol="mm",
            defaults={"description": "Millimeters"}
        )
        
        # Try to create performance results
        for i, row in data.iterrows():
            # Compressive strength
            if 'compressive_strength' in row and not pd.isna(row['compressive_strength']):
                comp_result = PerformanceResult.objects.create(
                    mix=mix,
                    category=PerformanceResult.HARDENED,
                    test_method=comp_method,
                    age_days=int(row['age_days']),
                    value_num=float(row['compressive_strength']),
                    unit=mpa_unit
                )
                logger.info(f"Created compressive strength result: {comp_result}")
            
            # Slump
            if 'slump' in row and not pd.isna(row['slump']):
                slump_result = PerformanceResult.objects.create(
                    mix=mix,
                    category=PerformanceResult.FRESH,
                    test_method=slump_method,
                    age_days=0,
                    value_num=float(row['slump']),
                    unit=mm_unit
                )
                logger.info(f"Created slump result: {slump_result}")
            
            # Only process the first row for testing
            break
    except Exception as e:
        logger.error(f"Error creating performance results: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting performance extraction test")
    test_direct_extraction()
    logger.info("Performance extraction test complete")
