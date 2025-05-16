#!/usr/bin/env python
"""
Test Dataset Importer for the Database Refresh Testing.

This module provides a specialized implementation of the BaseImporter for
the test dataset with a simple format used during Database Refresh Testing.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import datetime
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import base importer
from etl.base_importer import BaseImporter
from etl.standard_dataset_importer import StandardDatasetImporter

# Import Django models
from cdb_app.models import (
    MaterialClass, MaterialProperty, TestMethod, PerformanceResult, Material,
    ConcreteMix, MixComponent, PropertyDictionary, UnitLookup
)

class TestDatasetImporter(StandardDatasetImporter):
    """Importer for test dataset format used in Database Refresh Testing."""
    
    def __init__(self, dataset_code: str, csv_path: str, logger=None):
        """
        Initialize the test dataset importer.
        
        Args:
            dataset_code: Code identifying the dataset
            csv_path: Path to the CSV file
            logger: Optional logger instance
        """
        # Initialize parent but override its mappings
        super().__init__(dataset_code, csv_path, logger)
        
        # Define material mapping for test dataset
        self.material_mapping = {
            'cement': 'CEMENT',
            'water': 'WATER',
            'fine_aggregate': 'AGGR_F',
            'coarse_aggregate': 'AGGR_C',
            'fly_ash': 'SCM',
            'silica_fume': 'SCM',
            'superplasticizer': 'ADMIX'
        }
        
        # Initialize material class cache
        self.material_class_cache = {}
        
    def save_performance_results(self, results):
        """
        Save performance results to database.
        
        Args:
            results: List of result dictionaries
        
        Returns:
            int: Number of results saved
        """
        saved_count = 0
        
        # Debug: List all available units in the database
        all_units = list(UnitLookup.objects.all())
        self.logger.debug(f"Available units in database: {all_units}")
        
        # Debug: Check PerformanceResult model fields
        from django.db import models
        perf_fields = PerformanceResult._meta.get_fields()
        self.logger.debug(f"PerformanceResult fields: {[f.name for f in perf_fields]}")
        
        for result_data in results:
            try:
                # Debug the result data structure
                self.logger.debug(f"Processing result data: {result_data}")
                
                # Get or create test method
                test_method, _ = TestMethod.objects.get_or_create(
                    description=result_data['test_method_desc'],
                    defaults={'clause': ''}
                )
                
                # Get unit - it's required for PerformanceResult
                unit_symbol = result_data.get('unit_symbol', 'MPa')
                
                # Direct DB query to avoid any confusion with object attributes
                unit_record = None
                
                # Look up the unit record directly in the database
                unit_queryset = UnitLookup.objects.filter(unit_symbol=unit_symbol)
                if unit_queryset.exists():
                    unit_record = unit_queryset.first()
                    self.logger.debug(f"Found existing unit: {unit_record.unit_symbol} with ID {unit_record.unit_id}")
                else:
                    # Create a new unit if it doesn't exist
                    unit_record = UnitLookup.objects.create(
                        unit_symbol=unit_symbol,
                        description=f"Auto-created unit: {unit_symbol}",
                        si_factor=1.0
                    )
                    self.logger.debug(f"Created new unit with ID {unit_record.unit_id}: {unit_symbol}")
                
                # Use the unit_record for the result
                self.logger.debug(f"Using unit record with ID {unit_record.unit_id} for result")
                
                # Create performance result with all required fields
                # Note: property_name is not a field in the model, use it for logging only
                property_name = result_data.get('property_name', 'unknown')
                
                result = PerformanceResult(
                    mix=result_data['mix'],
                    category=result_data['category'],
                    test_method=test_method,
                    age_days=result_data['age_days'],
                    value_num=result_data['result_value'],
                    unit=unit_record  # Now using the unit_record
                )
                
                self.logger.debug(f"Creating PerformanceResult for property: {property_name}")
                
                # Save manually to capture any specific error
                try:
                    result.save()
                    self.logger.info(f"Successfully created performance result: {result}")
                    saved_count += 1
                    self.stats['results_imported'] += 1
                except Exception as save_error:
                    self.logger.error(f"Error during save(): {str(save_error)}")
                    raise save_error
                
            except Exception as e:
                self.logger.error(f"Error saving performance result: {str(e)}")
                # Print the full exception traceback for debugging
                import traceback
                self.logger.error(traceback.format_exc())
        
        return saved_count
    
    def extract_mix_data(self, row, qualified_mix_code) -> Dict:
        """
        Extract mix data from a test dataset row.
        
        Args:
            row: Pandas Series containing mix data
            qualified_mix_code: The qualified mix code for the mix
            
        Returns:
            Dict: Dictionary containing mix data
        """
        # Get mix date with fallback to today
        if 'date' in row and pd.notna(row['date']):
            try:
                # Try to parse the date from the CSV
                mix_date = pd.to_datetime(row['date']).date()
            except:
                # Fallback to today's date if parsing fails
                mix_date = datetime.now().date()
        else:
            # Default to today if no date column
            mix_date = datetime.now().date()
        
        # Create the mix data dictionary with column mappings from test dataset format
        mix_data = {
            'mix_code': qualified_mix_code,
            'date_created': mix_date,
            'region_country': row.get('country', 'Unknown'),  # Get country from 'country' column with default
            'strength_class': row.get('strength_class', '')   # Get strength class from 'strength_class' column
        }
        
        # Additional notes if provided
        if 'notes' in row and pd.notna(row['notes']):
            mix_data['notes'] = str(row['notes'])
        else:
            mix_data['notes'] = f'Imported from {self.dataset_code}'
        
        return mix_data
        
    def extract_mix_components(self, row) -> List[Dict]:
        """
        Extract mix components from a test dataset row.
        
        Args:
            row: Pandas Series containing mix data
            
        Returns:
            List[Dict]: List of component dictionaries
        """
        components = []
        
        # In our test dataset format, component names are direct column names
        material_columns = [
            'cement', 'water', 'fine_aggregate', 'coarse_aggregate', 
            'fly_ash', 'silica_fume', 'superplasticizer'
        ]
        
        for material_name in material_columns:
            if material_name in row and not pd.isna(row[material_name]) and row[material_name] > 0:
                if material_name in self.material_mapping:
                    material_class = self.material_mapping[material_name]
                    
                    # Prepare component data
                    component = {
                        'material_class': material_class,
                        'subtype_code': material_name,
                        'specific_name': material_name.replace('_', ' ').title(),
                        'manufacturer': 'Test Manufacturer',
                        'country': row.get('country', 'Norway'),
                        'dosage_kg_m3': float(row[material_name]),
                        'is_cementitious': material_class in ['CEMENT', 'SCM']
                    }
                    
                    components.append(component)
                else:
                    self.logger.warning(f"Unknown material type: {material_name}")
        
        return components
    
    def extract_performance_results(self, row, mix_obj) -> List[Dict]:
        """
        Extract performance results from a test dataset row.
        
        Args:
            row: Pandas Series containing mix data
            mix_obj: ConcreteMix object to associate with results
            
        Returns:
            List[Dict]: List of result dictionaries
        """
        results = []
        
        # Debug what data is available in the row
        self.logger.debug(f"Row data for performance extraction: {row.to_dict()}")
        
        # Look for compressive strength results - check multiple possible column names
        try:
            # Check all possible column names for compressive strength
            strength_column = None
            for col_name in ['compressive_strength', 'compressive_strength_MPa', 'compressive_strength_mpa']:
                if col_name in row and pd.notna(row[col_name]):
                    strength_column = col_name
                    break
                    
            if strength_column:
                strength_value = float(row[strength_column])
                if strength_value > 0:
                    result = {
                        'mix': mix_obj,
                        'category': PerformanceResult.HARDENED,
                        'result_value': strength_value,  # Changed from value_num to result_value
                        'unit_symbol': 'MPa',
                        'age_days': int(row.get('age_days', 28)),
                        'test_method_desc': 'EN 12390-3 Compressive Test',
                        'property_name': 'compressive_strength'  # Property name for backward compatibility
                    }
                    results.append(result)
                    self.logger.info(f"Extracted compressive strength: {strength_value} MPa at {result['age_days']} days")
        except Exception as e:
            self.logger.error(f"Error extracting compressive strength: {str(e)}")
        
        # Look for slump results - check multiple possible column names
        try:
            # Check all possible column names for slump
            slump_column = None
            for col_name in ['slump', 'slump_mm', 'target_slump_mm']:
                if col_name in row and pd.notna(row[col_name]):
                    slump_column = col_name
                    break
                    
            if slump_column:
                slump_value = float(row[slump_column])
                if slump_value > 0:
                    result = {
                        'mix': mix_obj,
                        'category': PerformanceResult.FRESH,
                        'result_value': slump_value,  # Changed from value_num to result_value
                        'unit_symbol': 'mm',
                        'age_days': 0,  # Fresh concrete property
                        'test_method_desc': 'EN 12350-2 Slump Test',
                        'property_name': 'slump'  # Property name for backward compatibility
                    }
                    results.append(result)
                    self.logger.info(f"Extracted slump: {slump_value} mm")
        except Exception as e:
            self.logger.error(f"Error extracting slump: {str(e)}")
        
        return results
        
    def create_or_get_dataset(self):
        """
        Create or get the dataset object for importing data.
        
        Returns:
            Dataset: The dataset object
        """
        from cdb_app.models import Dataset
        
        # Create or get dataset
        dataset_obj, created = Dataset.objects.get_or_create(
            dataset_name=self.dataset_code,
            defaults={
                "license": f"Test dataset for {self.dataset_code}",
                "description": f"Test dataset for database refresh testing"
            }
        )
        
        if created:
            self.logger.info(f"Created new dataset: {self.dataset_code}")
        else:
            self.logger.info(f"Using existing dataset: {self.dataset_code}")
        
        self.dataset_obj = dataset_obj
        return dataset_obj

    def import_data(self) -> bool:
        """
        Import test dataset.
        
        Returns:
            bool: True if import was successful
        """
        if not self.preprocess_data():
            return False
        
        self.logger.info(f"Importing {len(self.data)} mixes from dataset {self.dataset_code}")
        
        # Create the dataset record if it doesn't exist
        self.create_or_get_dataset()
        
        # Process each row
        for i, row in self.data.iterrows():
            try:
                # Get Mix Code - required
                mix_code = row.get('mix_code')
                if not mix_code:
                    self.handle_validation_error(i, "Missing mix_code")
                    continue
                
                # Create a qualified mix code with dataset prefix
                qualified_mix_code = f"{self.dataset_code}_{mix_code}"
                
                # Extract mix data from row
                mix_data = self.extract_mix_data(row, qualified_mix_code)
                
                # Extract components data from row
                components_data = self.extract_mix_components(row)
                
                # Create mix with components
                mix_obj = self.create_mix_with_components(mix_data, components_data)
                
                if mix_obj:
                    # Extract performance results
                    performance_results = self.extract_performance_results(row, mix_obj)
                    self.logger.info(f"Extracted {len(performance_results)} performance results for mix {qualified_mix_code}")
                    
                    # Debug each performance result before saving
                    for idx, result in enumerate(performance_results):
                        self.logger.debug(f"Performance result {idx+1}:")
                        for key, value in result.items():
                            self.logger.debug(f"  {key}: {value}")
                        
                        # Validate required fields
                        required_fields = ['mix', 'category', 'property_name', 'result_value', 'age_days', 'test_method_desc', 'unit_symbol']
                        missing = [field for field in required_fields if field not in result]
                        if missing:
                            self.logger.error(f"Missing required fields in result {idx+1}: {missing}")
                    
                    # Save performance results with detailed feedback
                    if performance_results:
                        try:
                            saved_count = self.save_performance_results(performance_results)
                            self.logger.info(f"Saved {saved_count} of {len(performance_results)} performance results")
                        except Exception as save_err:
                            self.logger.error(f"Error saving performance results: {str(save_err)}")
                            import traceback
                            self.logger.error(traceback.format_exc())
                else:
                    self.logger.error(f"Failed to create mix for row {i}: {mix_data}")
                    self.stats['mixes_failed'] += 1
            
            except Exception as e:
                self.logger.error(f"Error processing row {i}: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                self.stats['mixes_failed'] += 1
        
        self.logger.info(f"Import completed: {self.stats['mixes_imported']} mixes imported")
        return self.stats['mixes_imported'] > 0


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) < 3:
        print("Usage: python test_dataset_importer.py <dataset_code> <csv_path>")
        sys.exit(1)
    
    dataset_code = sys.argv[1]
    csv_path = sys.argv[2]
    
    importer = TestDatasetImporter(dataset_code, csv_path)
    stats = importer.run()
    
    print(f"Import complete with stats: {stats}")
