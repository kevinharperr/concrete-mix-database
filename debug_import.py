#!/usr/bin/env python
# debug_import.py - Script to debug the test dataset importer

import os
import sys
import logging
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
django.setup()

from etl.test_dataset_importer import TestDatasetImporter

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('debug_importer')

# Set all loggers to debug level
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.DEBUG)

def main():
    """Run the test dataset importer with verbose debugging."""
    dataset_code = 'TEST_DS'
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etl', 'test_dataset.csv')
    
    logger.info(f"Initializing importer for {dataset_code} from {csv_path}")
    importer = TestDatasetImporter(dataset_code, csv_path, logger=logger)
    
    # Load data and show first few rows to verify content
    importer.load_data()
    if importer.data is not None:
        logger.info(f"Data loaded successfully, {len(importer.data)} rows found")
        logger.info(f"First row: {importer.data.iloc[0].to_dict()}")
        
        # Test extracting performance results from the first row
        row = importer.data.iloc[0]
        logger.info(f"Testing performance result extraction for first row:")
        logger.info(f"Compressive strength: {row.get('compressive_strength')}")
        logger.info(f"Slump: {row.get('slump')}")
        
        # Import the data
        logger.info("Starting data import...")
        import_success = importer.import_data()
        stats = importer.stats
        
        logger.info(f"Import complete, success: {import_success}")
        logger.info(f"Stats: {stats}")
        
    else:
        logger.error("Failed to load data")

if __name__ == "__main__":
    main()
