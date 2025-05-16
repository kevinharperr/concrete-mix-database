#!/usr/bin/env python
"""
Standard Dataset Importer for the Concrete Mix Database.

This module provides an implementation of the BaseImporter for standard CSV-based
datasets with a predefined format. It includes specific validation and transformation
logic for standardized datasets.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import base importer
from etl.base_importer import BaseImporter

# Import Django models
from cdb_app.models import (
    MaterialClass, MaterialProperty, TestMethod, PerformanceResult, Material,
    ConcreteMix, MixComponent
)

class StandardDatasetImporter(BaseImporter):
    """Importer for standardized dataset format."""
    
    def __init__(self, dataset_code: str, csv_path: str, logger=None, 
                 material_mapping=None, column_mapping=None):
        """
        Initialize the standard dataset importer.
        
        Args:
            dataset_code: Code identifying the dataset
            csv_path: Path to the CSV file
            logger: Optional logger instance
            material_mapping: Optional mapping of material names to class codes
            column_mapping: Optional mapping of CSV columns to database fields
        """
        super().__init__(dataset_code, csv_path, logger)
        
        # Default mappings if not provided
        self.material_mapping = material_mapping or {
            'cement': 'CEMENT',
            'water': 'WATER',
            'fine_aggregate': 'AGGR_F',
            'coarse_aggregate': 'AGGR_C',
            'fly_ash': 'SCM',
            'slag': 'SCM',
            'silica_fume': 'SCM',
            'superplasticizer': 'ADMIX',
            'air_entrainer': 'ADMIX',
            'accelerator': 'ADMIX',
            'retarder': 'ADMIX'
        }
        
        self.column_mapping = column_mapping or {
            'mix_id': 'mix_code',
            'date': 'date_created',
            'country': 'region_country',
            'strength_class': 'strength_class',
            'slump': 'target_slump_mm',
            'compressive_strength': 'compressive_strength_MPa',
            'age_days': 'age_days'
        }
        
        # Initialize material class cache
        self.material_class_cache = {}
    
    def _get_material_class(self, class_code):
        """Get material class from cache or database."""
        if class_code not in self.material_class_cache:
            self.material_class_cache[class_code] = MaterialClass.objects.get(class_code=class_code)
        return self.material_class_cache[class_code]
    
    def preprocess_data(self):
        """Preprocess the dataset to standardize column names and values."""
        self.logger.info("Preprocessing dataset")
        
        if self.data is None:
            self.logger.error("No data loaded to preprocess")
            return False
        
        try:
            # Rename columns based on mapping
            col_map = {k: v for k, v in self.column_mapping.items() if k in self.data.columns}
            self.data.rename(columns=col_map, inplace=True)
            
            # Ensure date column is datetime
            if 'date_created' in self.data.columns:
                self.data['date_created'] = pd.to_datetime(
                    self.data['date_created'], errors='coerce'
                ).dt.date
            
            # Fill missing values where appropriate
            self.data['region_country'] = self.data.get('region_country', 'Unknown')
            self.data['notes'] = self.data.get('notes', f"Imported from {self.dataset_code}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error in preprocessing: {str(e)}")
            return False
    
    def extract_mix_components(self, row) -> List[Dict]:
        """
        Extract mix components from a data row.
        
        Args:
            row: Pandas Series containing mix data
            
        Returns:
            List[Dict]: List of component dictionaries
        """
        components = []
        
        # Pattern: column name format is expected to be 'material_dosage_kg_m3'
        # e.g., 'cement_dosage_kg_m3', 'water_dosage_kg_m3', etc.
        for col in row.index:
            if col.endswith('_dosage_kg_m3') and not pd.isna(row[col]) and row[col] > 0:
                material_type = col.replace('_dosage_kg_m3', '')
                
                if material_type in self.material_mapping:
                    material_class = self.material_mapping[material_type]
                    
                    # Prepare component data
                    component = {
                        'material_class': material_class,
                        'subtype_code': material_type,
                        'specific_name': row.get(f"{material_type}_name", material_type),
                        'manufacturer': row.get(f"{material_type}_manufacturer", None),
                        'country': row.get(f"{material_type}_origin", None),
                        'dosage_kg_m3': float(row[col]),
                        'is_cementitious': material_class in ['CEMENT', 'SCM']
                    }
                    
                    components.append(component)
                else:
                    self.logger.warning(f"Unknown material type: {material_type}")
        
        return components
    
    def extract_performance_results(self, row, mix_obj) -> List[Dict]:
        """
        Extract performance results from a data row.
        
        Args:
            row: Pandas Series containing mix data
            mix_obj: ConcreteMix object to associate with results
            
        Returns:
            List[Dict]: List of result dictionaries
        """
        results = []
        
        # Look for compressive strength results
        if 'compressive_strength_MPa' in row and not pd.isna(row['compressive_strength_MPa']):
            result = {
                'mix': mix_obj,
                'property_name': 'compressive_strength',
                'property_value': float(row['compressive_strength_MPa']),
                'unit': 'MPa',
                'age_days': int(row.get('age_days', 28)),
                'test_method': 'ASTM C39' if row.get('region_country') == 'USA' else 'EN 12390-3'
            }
            results.append(result)
        
        # Look for slump results
        if 'slump_mm' in row and not pd.isna(row['slump_mm']):
            result = {
                'mix': mix_obj,
                'property_name': 'slump',
                'property_value': float(row['slump_mm']),
                'unit': 'mm',
                'age_days': 0,
                'test_method': 'ASTM C143' if row.get('region_country') == 'USA' else 'EN 12350-2'
            }
            results.append(result)
        
        return results
    
    def save_performance_results(self, results):
        """
        Save performance results to database.
        
        Args:
            results: List of result dictionaries
        
        Returns:
            int: Number of results saved
        """
        saved_count = 0
        
        for result_data in results:
            try:
                # Get or create test method
                test_method, _ = TestMethod.objects.get_or_create(
                    method_name=result_data['test_method']
                )
                
                # Create performance result
                PerformanceResult.objects.create(
                    mix=result_data['mix'],
                    property_name=result_data['property_name'],
                    property_value=result_data['property_value'],
                    unit=result_data['unit'],
                    age_days=result_data['age_days'],
                    test_method=test_method
                )
                
                saved_count += 1
                self.stats['results_imported'] += 1
            
            except Exception as e:
                self.logger.error(f"Error saving performance result: {str(e)}")
        
        return saved_count
    
    def import_data(self) -> bool:
        """
        Import standardized dataset.
        
        Returns:
            bool: True if import was successful
        """
        if not self.preprocess_data():
            return False
        
        self.logger.info(f"Importing {len(self.data)} mixes")
        
        for _, row in self.data.iterrows():
            try:
                # Extract mix data
                mix_data = {
                    'mix_code': row.get('mix_code', f"{self.dataset_code}_mix{_}"),
                    'date_created': row.get('date_created'),
                    'region_country': row.get('region_country'),
                    'strength_class': row.get('strength_class'),
                    'target_slump_mm': row.get('target_slump_mm')
                }
                
                # Extract components
                components = self.extract_mix_components(row)
                self.stats['components_total'] += len(components)
                
                # Validate and create mix with components
                mix_obj = self.create_mix_with_components(mix_data, components)
                
                if mix_obj:
                    # Extract and save performance results
                    results = self.extract_performance_results(row, mix_obj)
                    self.stats['results_total'] += len(results)
                    self.save_performance_results(results)
            
            except Exception as e:
                self.logger.error(f"Error processing row {_}: {str(e)}")
                self.stats['mixes_failed'] += 1
        
        self.logger.info(f"Import completed: {self.stats['mixes_imported']} mixes imported")
        return self.stats['mixes_imported'] > 0


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) < 3:
        print("Usage: python standard_dataset_importer.py <dataset_code> <csv_path>")
        sys.exit(1)
    
    dataset_code = sys.argv[1]
    csv_path = sys.argv[2]
    
    importer = StandardDatasetImporter(dataset_code, csv_path)
    stats = importer.run()
    
    print(f"Import complete with stats: {stats}")
