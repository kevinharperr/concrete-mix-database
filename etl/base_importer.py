#!/usr/bin/env python
"""
Base dataset importer with robust validation for the Concrete Mix Database.

This module provides a foundation for all dataset importers with
built-in validation, logging, and error handling.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional, Any

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')

import django
django.setup()

# Import Django models
from django.db import transaction
from django.db.models import Q
from cdb_app.models import (
    Dataset, Material, MaterialClass, UnitLookup, PropertyDictionary,
    ConcreteMix, MixComponent, PerformanceResult, MaterialProperty,
    CementDetail, ScmDetail, AggregateDetail, AdmixtureDetail,
    BibliographicReference, ConcreteMixReference, Specimen, TestMethod
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('etl_import.log')
    ]
)

class BaseImporter:
    """Base class for all dataset importers with validation."""
    
    def __init__(self, dataset_code: str, csv_path: str, logger=None):
        """
        Initialize the importer.
        
        Args:
            dataset_code: Code identifying the dataset (e.g., 'DS1')
            csv_path: Path to the CSV file containing the data
            logger: Optional logger instance
        """
        self.dataset_code = dataset_code
        self.csv_path = csv_path
        self.logger = logger or logging.getLogger(f"{dataset_code}_importer")
        self.data = None
        self.dataset_obj = None
        
        # Track statistics
        self.stats = {
            'mixes_total': 0,
            'mixes_imported': 0,
            'mixes_skipped': 0,
            'mixes_failed': 0,
            'components_total': 0,
            'components_imported': 0,
            'results_total': 0,
            'results_imported': 0,
            'validation_failures': {}
        }
        
        # Define validation thresholds
        self.validation_thresholds = {
            'min_w_b_ratio': 0.25,
            'max_w_b_ratio': 0.70,
            'min_components': 3,  # At minimum: cement, water, aggregate
            'cement_class_codes': ['CEMENT'],
            'water_class_codes': ['WATER'],
            'aggregate_class_codes': ['AGGR_C', 'AGGR_F'],
            'min_cement_content': 100,  # kg/m3
            'max_cement_content': 600,  # kg/m3
            'min_water_content': 100,   # kg/m3
            'max_water_content': 300    # kg/m3
        }
    
    def load_data(self) -> bool:
        """
        Load data from the CSV file.
        
        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Loading data from {self.csv_path}")
            self.data = pd.read_csv(self.csv_path)
            self.stats['mixes_total'] = len(self.data)
            self.logger.info(f"Loaded {len(self.data)} rows from CSV")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load data: {str(e)}")
            return False
    
    def get_or_create_dataset(self) -> bool:
        """
        Get or create the dataset entry.
        
        Returns:
            bool: True if dataset was retrieved or created, False otherwise
        """
        try:
            self.dataset_obj, created = Dataset.objects.get_or_create(
                dataset_name=self.dataset_code,
                defaults={'license': f'Imported from {self.dataset_code}'}
            )
            if created:
                self.logger.info(f"Created new dataset: {self.dataset_code}")
            else:
                self.logger.info(f"Using existing dataset: {self.dataset_code}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to get or create dataset: {str(e)}")
            return False
    
    def validate_mix_data(self, mix_data: Dict) -> Tuple[bool, Dict]:
        """
        Validate mix data against defined thresholds.
        
        Args:
            mix_data: Dictionary containing mix data
            
        Returns:
            Tuple[bool, Dict]: (is_valid, validation_results)
        """
        validation_results = {
            'is_valid': True,
            'issues': []
        }
        
        # Example validation checks
        # (Derived classes would implement specific validation logic)
        try:
            # Check for required fields
            required_fields = ['mix_code']
            for field in required_fields:
                if field not in mix_data or pd.isna(mix_data[field]):
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(f"Missing required field: {field}")
            
            # More specific validations would go here
                    
        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")
            
        return validation_results['is_valid'], validation_results
    
    def calculate_water_binder_ratio(self, components: List[Dict]) -> Tuple[float, bool]:
        """
        Calculate the water-binder ratio from mix components.
        
        Args:
            components: List of component dictionaries with material class and dosage
            
        Returns:
            Tuple[float, bool]: (w/b ratio, is_valid)
        """
        water_content = sum(c['dosage_kg_m3'] for c in components 
                          if c['material_class'] in self.validation_thresholds['water_class_codes'])
        
        binder_content = sum(c['dosage_kg_m3'] for c in components 
                           if c['material_class'] in self.validation_thresholds['cement_class_codes'] 
                           or (c.get('is_cementitious', False) and c['material_class'] == 'SCM'))
        
        if binder_content == 0:
            return 0.0, False
        
        wb_ratio = water_content / binder_content
        
        # Validate the calculated ratio
        is_valid = (self.validation_thresholds['min_w_b_ratio'] <= wb_ratio <= 
                    self.validation_thresholds['max_w_b_ratio'])
        
        return round(wb_ratio, 3), is_valid
    
    def validate_mix_components(self, components: List[Dict]) -> Tuple[bool, Dict]:
        """
        Validate mix components for completeness and reasonable values.
        
        Args:
            components: List of component dictionaries
            
        Returns:
            Tuple[bool, Dict]: (is_valid, validation_results)
        """
        validation_results = {
            'is_valid': True,
            'issues': [],
            'w_b_ratio': None,
            'has_cement': False,
            'has_water': False,
            'has_aggregate': False
        }
        
        # Check for minimum number of components
        if len(components) < self.validation_thresholds['min_components']:
            validation_results['is_valid'] = False
            validation_results['issues'].append(
                f"Too few components: {len(components)} < {self.validation_thresholds['min_components']}"
            )
        
        # Check for required material types
        for component in components:
            if component['material_class'] in self.validation_thresholds['cement_class_codes']:
                validation_results['has_cement'] = True
                # Validate cement content
                if component['dosage_kg_m3'] < self.validation_thresholds['min_cement_content']:
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(
                        f"Cement content too low: {component['dosage_kg_m3']} kg/m³"
                    )
                elif component['dosage_kg_m3'] > self.validation_thresholds['max_cement_content']:
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(
                        f"Cement content too high: {component['dosage_kg_m3']} kg/m³"
                    )
            
            elif component['material_class'] in self.validation_thresholds['water_class_codes']:
                validation_results['has_water'] = True
                # Validate water content
                if component['dosage_kg_m3'] < self.validation_thresholds['min_water_content']:
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(
                        f"Water content too low: {component['dosage_kg_m3']} kg/m³"
                    )
                elif component['dosage_kg_m3'] > self.validation_thresholds['max_water_content']:
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(
                        f"Water content too high: {component['dosage_kg_m3']} kg/m³"
                    )
            
            elif component['material_class'] in self.validation_thresholds['aggregate_class_codes']:
                validation_results['has_aggregate'] = True
        
        # Check for missing essential components
        if not validation_results['has_cement']:
            validation_results['is_valid'] = False
            validation_results['issues'].append("Missing cement component")
        
        if not validation_results['has_water']:
            validation_results['is_valid'] = False
            validation_results['issues'].append("Missing water component")
        
        if not validation_results['has_aggregate']:
            validation_results['is_valid'] = False
            validation_results['issues'].append("Missing aggregate component")
        
        # Calculate and validate W/B ratio
        if validation_results['has_cement'] and validation_results['has_water']:
            wb_ratio, ratio_valid = self.calculate_water_binder_ratio(components)
            validation_results['w_b_ratio'] = wb_ratio
            
            if not ratio_valid:
                validation_results['is_valid'] = False
                validation_results['issues'].append(
                    f"W/B ratio out of range: {wb_ratio} not in "
                    f"[{self.validation_thresholds['min_w_b_ratio']}, "
                    f"{self.validation_thresholds['max_w_b_ratio']}]"
                )
        
        return validation_results['is_valid'], validation_results
    
    def get_or_create_material(self, material_data: Dict) -> Tuple[Optional[Material], bool]:
        """
        Get or create a material entry.
        
        Args:
            material_data: Dictionary containing material data
            
        Returns:
            Tuple[Optional[Material], bool]: (material_obj, created)
        """
        try:
            # Get material class
            mat_class = MaterialClass.objects.get(class_code=material_data['material_class'])
            
            # Check if similar material exists
            material_obj = Material.objects.filter(
                material_class=mat_class,
                subtype_code=material_data.get('subtype_code'),
                specific_name=material_data.get('specific_name')
            ).first()
            
            if material_obj:
                return material_obj, False
            
            # Create new material if it doesn't exist
            material_obj = Material.objects.create(
                material_class=mat_class,
                subtype_code=material_data.get('subtype_code'),
                specific_name=material_data.get('specific_name'),
                manufacturer=material_data.get('manufacturer'),
                country_of_origin=material_data.get('country'),
                source_dataset=self.dataset_code
            )
            
            return material_obj, True
        
        except Exception as e:
            self.logger.error(f"Failed to get or create material: {str(e)}")
            return None, False
    
    def create_mix_with_components(self, mix_data: Dict, components_data: List[Dict]) -> Optional[ConcreteMix]:
        """
        Create a concrete mix with components.
        
        Args:
            mix_data: Dictionary containing mix data
            components_data: List of dictionaries containing component data
            
        Returns:
            Optional[ConcreteMix]: Created mix object or None if failed
        """
        try:
            # Validate mix components
            components_valid, validation_results = self.validate_mix_components(components_data)
            
            if not components_valid:
                self.logger.warning(
                    f"Mix {mix_data.get('mix_code')} has invalid components: "
                    f"{', '.join(validation_results['issues'])}"
                )
                self.stats['mixes_skipped'] += 1
                
                # Record validation failure type
                for issue in validation_results['issues']:
                    issue_type = issue.split(':')[0]
                    self.stats['validation_failures'][issue_type] = (
                        self.stats['validation_failures'].get(issue_type, 0) + 1
                    )
                
                return None
            
            # Create mix
            with transaction.atomic():
                mix_obj = ConcreteMix.objects.create(
                    dataset=self.dataset_obj,
                    mix_code=mix_data.get('mix_code'),
                    date_created=mix_data.get('date_created'),
                    region_country=mix_data.get('region_country'),
                    strength_class=mix_data.get('strength_class'),
                    target_slump_mm=mix_data.get('target_slump_mm'),
                    w_b_ratio=validation_results['w_b_ratio'],
                    notes=f"Imported from {self.dataset_code}"
                )
                
                # Create components
                for comp_data in components_data:
                    material_obj, _ = self.get_or_create_material(comp_data)
                    
                    if material_obj:
                        MixComponent.objects.create(
                            mix=mix_obj,
                            material=material_obj,
                            dosage_kg_m3=comp_data['dosage_kg_m3'],
                            is_cementitious=comp_data.get('is_cementitious', False)
                        )
                        self.stats['components_imported'] += 1
                
                self.stats['mixes_imported'] += 1
                return mix_obj
        
        except Exception as e:
            self.logger.error(f"Failed to create mix: {str(e)}")
            self.stats['mixes_failed'] += 1
            return None
    
    def import_data(self) -> bool:
        """
        Main method to import data.
        Derived classes should implement this method.
        
        Returns:
            bool: True if import was successful, False otherwise
        """
        raise NotImplementedError("Derived classes must implement import_data()")
    
    def run(self) -> Dict:
        """
        Run the import process.
        
        Returns:
            Dict: Import statistics
        """
        self.logger.info(f"Starting import for dataset {self.dataset_code}")
        
        # Load data
        if not self.load_data():
            return self.stats
        
        # Get or create dataset
        if not self.get_or_create_dataset():
            return self.stats
        
        # Import data
        success = self.import_data()
        
        # Log statistics
        self.logger.info(f"Import statistics: {self.stats}")
        
        return self.stats
