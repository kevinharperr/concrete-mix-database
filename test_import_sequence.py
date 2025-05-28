#!/usr/bin/env python
"""
Test Import Sequence for Phase 3 of the Database Refresh Plan.

This script:
1. Imports reference/lookup tables first
2. Tests a single dataset import with the ETL framework
3. Validates results and documents any issues encountered

Run this on the staging database during the database refresh plan.
"""
import os
import sys
import datetime
import logging
import pandas as pd
from typing import Dict, List, Optional

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')

import django
django.setup()

from django.db import transaction
from django.db.models import Count, Q
from refresh_status.models import DatabaseStatus, RefreshLogEntry

# Import models and importer
from cdb_app.models import (
    Dataset, Material, MaterialClass, UnitLookup, PropertyDictionary,
    ConcreteMix, MixComponent, PerformanceResult, TestMethod, Standard
)
from etl.test_dataset_importer import TestDatasetImporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_import.log')
    ]
)
logger = logging.getLogger('test_import')

class TestImportSequence:
    """Manages the test import sequence for the database refresh."""

    def __init__(self):
        self.stats = {
            'reference_tables_imported': 0,
            'reference_records_created': 0,
            'dataset_imported': False,
            'mixes_imported': 0,
            'components_imported': 0,
            'results_imported': 0,
            'issues': []
        }
        self.start_time = datetime.datetime.now()

    def update_status(self, step: str, message: str, is_error: bool = False):
        """Update the database status and log an entry."""
        try:
            # Get current status
            status = DatabaseStatus.objects.latest('last_updated')
            
            # Create log entry
            RefreshLogEntry.objects.create(
                phase="Phase 3: Test Migration",
                step=step,
                status="error" if is_error else "info",
                message=message,
                is_error=is_error
            )
            
            # Update status details
            status.current_step = f"Test Import: {step}"
            status.progress_percentage = 20  # Adjust based on progress
            if is_error:
                status.error_message = message
            status.save()
            
            logger.info(f"Status updated: {message}")
            
        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}")
    
    def import_reference_tables(self):
        """Import essential reference and lookup tables."""
        logger.info("Importing reference tables...")
        self.update_status("Reference Tables", "Importing reference tables")
        
        try:
            # Create standards
            standards = [
                {'code': 'EN 12390-3', 'title': 'Testing hardened concrete - Compressive strength'},
                {'code': 'ASTM C39', 'title': 'Standard Test Method for Compressive Strength'},
                {'code': 'EN 12350-2', 'title': 'Testing fresh concrete - Slump-test'},
                {'code': 'ASTM C143', 'title': 'Standard Test Method for Slump of Concrete'}
            ]
            
            for std in standards:
                Standard.objects.get_or_create(
                    code=std['code'],
                    defaults={'title': std['title']}
                )
                self.stats['reference_records_created'] += 1
            
            # Create test methods with references to standards
            test_methods = [
                {'description': 'EN 12390-3 Compressive Test', 'standard_code': 'EN 12390-3', 'clause': ''},
                {'description': 'ASTM C39 Compressive Test', 'standard_code': 'ASTM C39', 'clause': ''},
                {'description': 'EN 12350-2 Slump Test', 'standard_code': 'EN 12350-2', 'clause': ''},
                {'description': 'ASTM C143 Slump Test', 'standard_code': 'ASTM C143', 'clause': ''}
            ]
            
            for tm in test_methods:
                standard = Standard.objects.get(code=tm['standard_code'])
                TestMethod.objects.get_or_create(
                    description=tm['description'],
                    defaults={'standard': standard, 'clause': tm['clause']}
                )
                self.stats['reference_records_created'] += 1
            
            # Create property dictionary entries
            properties = [
                {'property_name': 'compressive_strength', 'unit_symbol': 'MPa', 'display_name': 'Compressive Strength (MPa)', 'property_group': PropertyDictionary.MECHANICAL},
                {'property_name': 'slump', 'unit_symbol': 'mm', 'display_name': 'Slump (mm)', 'property_group': PropertyDictionary.PHYSICAL},
                {'property_name': 'water_binder_ratio', 'unit_symbol': '', 'display_name': 'Water/Binder Ratio', 'property_group': PropertyDictionary.PHYSICAL},
                {'property_name': 'density', 'unit_symbol': 'kg/m³', 'display_name': 'Density (kg/m³)', 'property_group': PropertyDictionary.PHYSICAL}
            ]
            
            for prop in properties:
                unit = UnitLookup.objects.get(unit_symbol=prop['unit_symbol']) if prop['unit_symbol'] else None
                PropertyDictionary.objects.get_or_create(
                    property_name=prop['property_name'],
                    defaults={
                        'display_name': prop['display_name'],
                        'property_group': prop['property_group'],
                        'default_unit': unit
                    }
                )
                self.stats['reference_records_created'] += 1
            
            self.stats['reference_tables_imported'] = 3  # Standards, TestMethods, PropertyDictionary
            logger.info(f"Imported {self.stats['reference_records_created']} reference records")
            self.update_status("Reference Tables", f"Successfully imported {self.stats['reference_records_created']} reference records")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import reference tables: {str(e)}")
            self.update_status("Reference Tables", f"Failed to import: {str(e)}", True)
            self.stats['issues'].append(f"Reference tables import failed: {str(e)}")
            return False
    
    def import_test_dataset(self, dataset_code, csv_path):
        """Import a test dataset using the TestDatasetImporter."""
        logger.info(f"Importing test dataset {dataset_code} from {csv_path}")
        self.update_status("Dataset Import", f"Importing test dataset {dataset_code}")
        
        # Record performance metrics
        import_start_time = datetime.datetime.now()
        memory_before = self._get_memory_usage()
        
        try:
            # Verify CSV file exists and is readable
            if not os.path.exists(csv_path):
                error_msg = f"CSV file not found at path: {csv_path}"
                logger.error(error_msg)
                self.update_status("Dataset Import", error_msg, True)
                self.stats['issues'].append(error_msg)
                return False
            
            # Check file size for logging purposes
            file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
            logger.info(f"Dataset file size: {file_size_mb:.2f} MB")
            
            # Preview CSV content (first 5 rows) for debugging purposes
            try:
                df_preview = pd.read_csv(csv_path, nrows=5)
                logger.info(f"CSV preview - columns: {list(df_preview.columns)}")
                logger.debug(f"CSV preview - first 5 rows: {df_preview.head().to_dict()}")
                
                # Following best practice: Check for required columns based on lessons learned
                required_columns = ['mix_id', 'compressive_strength', 'slump']
                # Handle column name transformations (lesson learned)
                actual_columns = set(df_preview.columns)
                transformed_columns = {col.replace('_MPa', '').lower() for col in actual_columns}
                
                missing_columns = []
                for col in required_columns:
                    if col not in actual_columns and col not in transformed_columns:
                        missing_columns.append(col)
                
                if missing_columns:
                    warning_msg = f"Warning: Missing expected columns in dataset: {missing_columns}"
                    logger.warning(warning_msg)
                    self.stats['issues'].append(warning_msg)
            except Exception as e:
                logger.warning(f"Could not preview CSV file: {str(e)}")
            
            # Create a TestDatasetImporter with our test dataset
            logger.info("Initializing TestDatasetImporter...")
            importer = TestDatasetImporter(dataset_code, csv_path, logger=logger)
            
            # Run the import with transaction control and performance monitoring
            with transaction.atomic():
                stats = importer.run()
                
                # Record performance metrics
                import_end_time = datetime.datetime.now()
                import_duration = (import_end_time - import_start_time).total_seconds()
                memory_after = self._get_memory_usage()
                memory_used = memory_after - memory_before
                
                performance_stats = {
                    'import_duration_seconds': import_duration,
                    'memory_used_mb': memory_used,
                    'rows_per_second': stats.get('rows_processed', 0) / max(import_duration, 0.001),
                    'file_size_mb': file_size_mb
                }
                
                logger.info(f"Import performance: {performance_stats}")
                self.stats['performance'] = performance_stats
            
            if stats['mixes_imported'] > 0:
                self.stats['dataset_imported'] = True
                self.stats['mixes_imported'] = stats['mixes_imported']
                self.stats['components_imported'] = stats['components_imported']
                self.stats['results_imported'] = stats['results_imported']
                
                logger.info(f"Successfully imported {stats['mixes_imported']} mixes")
                success_msg = (f"Imported {stats['mixes_imported']} mixes, " +
                              f"{stats['components_imported']} components, " +
                              f"{stats['results_imported']} results " +
                              f"in {performance_stats['import_duration_seconds']:.2f} seconds")
                self.update_status("Dataset Import", success_msg)
                return True
            else:
                logger.warning(f"No mixes were imported from {dataset_code}")
                self.update_status("Dataset Import", f"No mixes were imported from {dataset_code}", True)
                self.stats['issues'].append(f"Dataset import yielded 0 mixes: {stats}")
                return False
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Failed to import dataset: {str(e)}\n{error_traceback}")
            self.update_status("Dataset Import", f"Failed to import dataset: {str(e)}", True)
            self.stats['issues'].append(f"Dataset import failed: {str(e)}")
            return False
    
    def _get_memory_usage(self):
        """Get the current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except ImportError:
            logger.warning("psutil not installed, cannot track memory usage")
            return 0
        except Exception as e:
            logger.warning(f"Error getting memory usage: {str(e)}")
            return 0
    
    def performance_test_import(self, dataset_path):
        """Run performance tests on the import process."""
        logger.info("Starting import performance testing...")
        self.update_status("Performance Testing", "Testing import performance")
        
        performance_results = {
            'success': True,
            'metrics': [],
            'issues': []
        }
        
        try:
            # Test full import performance
            start_time = datetime.datetime.now()
            dataset_success = self.import_test_dataset('PERF_TEST', dataset_path)
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if not dataset_success:
                performance_results['success'] = False
                performance_results['issues'].append("Import failed during performance testing")
                return performance_results
            
            # Record overall performance
            performance_results['metrics'].append({
                'test_name': 'full_import',
                'duration_seconds': duration,
                'mixes_imported': self.stats['mixes_imported'],
                'components_imported': self.stats['components_imported'],
                'results_imported': self.stats['results_imported']
            })
            
            # Test component load times (if we have successful import data)
            if dataset_success:
                # Test query performance for components
                component_query_start = datetime.datetime.now()
                component_count = MixComponent.objects.filter(mix__dataset__dataset_name='PERF_TEST').count()
                component_query_end = datetime.datetime.now()
                component_query_duration = (component_query_end - component_query_start).total_seconds()
                
                performance_results['metrics'].append({
                    'test_name': 'component_query',
                    'duration_seconds': component_query_duration,
                    'record_count': component_count
                })
                
                # Test query performance for performance results
                results_query_start = datetime.datetime.now()
                results_count = PerformanceResult.objects.filter(mix__dataset__dataset_name='PERF_TEST').count()
                results_query_end = datetime.datetime.now()
                results_query_duration = (results_query_end - results_query_start).total_seconds()
                
                performance_results['metrics'].append({
                    'test_name': 'results_query',
                    'duration_seconds': results_query_duration,
                    'record_count': results_count
                })
            
            # Log performance results
            logger.info(f"Performance test results: {performance_results}")
            self.update_status("Performance Testing", "Import performance testing completed")
            
            return performance_results
            
        except Exception as e:
            logger.error(f"Performance testing failed: {str(e)}")
            self.update_status("Performance Testing", f"Performance testing failed: {str(e)}", True)
            performance_results['success'] = False
            performance_results['issues'].append(str(e))
            return performance_results
    
    def validate_import_results(self):
        """Validate the imported data for consistency and relationships."""
        logger.info("Validating import results...")
        self.update_status("Validation", "Validating import results")
        
        validation_results = {
            'success': True,
            'issues': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Verify model fields exist using Django's introspection capabilities
            # (Lesson learned: Always verify model fields before using them)
            logger.info("Verifying model fields...")
            model_fields = {}
            for model_class in [Dataset, ConcreteMix, MixComponent, PerformanceResult, UnitLookup]:
                model_name = model_class.__name__
                model_fields[model_name] = [f.name for f in model_class._meta.get_fields()]
                logger.debug(f"{model_name} fields: {model_fields[model_name]}")
            
            validation_results['details']['model_fields'] = model_fields
            
            # Check if dataset exists
            dataset = Dataset.objects.filter(dataset_name='TEST_DS').first()
            if not dataset:
                validation_results['issues'].append("Dataset 'TEST_DS' not found")
                validation_results['success'] = False
            
            # Check if mixes were created
            mixes_count = ConcreteMix.objects.filter(dataset=dataset).count() if dataset else 0
            if mixes_count == 0:
                validation_results['issues'].append("No mixes found in the dataset")
                validation_results['success'] = False
            else:
                validation_results['details']['mixes_count'] = mixes_count
                logger.info(f"Found {mixes_count} mixes in dataset")
            
            # Check if components were created for each mix
            if mixes_count > 0:
                # Get mixes without components
                mixes_without_components = ConcreteMix.objects.filter(
                    dataset=dataset
                ).annotate(
                    component_count=Count('components')
                ).filter(
                    component_count=0
                )
                
                if mixes_without_components.exists():
                    missing_components_mixes = list(mixes_without_components.values_list('mix_code', flat=True))
                    validation_results['issues'].append(
                        f"{mixes_without_components.count()} mixes have no components: {missing_components_mixes}"
                    )
                    validation_results['success'] = False
                
                # Check for mixes missing essential components (cement, water)
                # Lesson learned: Validate required components
                essential_materials = {
                    'CEMENT': 'cement',
                    'WATER': 'water'
                }
                
                for material_class, material_name in essential_materials.items():
                    # First try to find the material class ID
                    try:
                        material_class_obj = MaterialClass.objects.filter(
                            name__icontains=material_name
                        ).first()
                        
                        if material_class_obj:
                            # Now use the material class object to find mixes missing this component type
                            mixes_missing_essential = ConcreteMix.objects.filter(
                                dataset=dataset
                            ).exclude(
                                components__material__material_class=material_class_obj
                            ).values_list('mix_code', flat=True)
                        else:
                            logger.warning(f"Could not find material class for {material_name}")
                            mixes_missing_essential = []
                    except Exception as e:
                        logger.warning(f"Error checking for {material_name} components: {str(e)}")
                        mixes_missing_essential = []
                    
                    if mixes_missing_essential:
                        validation_results['issues'].append(
                            f"{len(mixes_missing_essential)} mixes missing {component_type}: {list(mixes_missing_essential)}"
                        )
                        validation_results['success'] = False
            
            # Check if performance results were created with detailed analysis per category
            if dataset:
                # Count overall results
                results_count = PerformanceResult.objects.filter(mix__dataset=dataset).count()
                
                if results_count == 0:
                    validation_results['issues'].append("No performance results found")
                    validation_results['success'] = False
                else:
                    validation_results['details']['results_count'] = results_count
                    logger.info(f"Found {results_count} performance results")
                    
                    # Check results by category (hardened, fresh)
                    for category in ['hardened', 'fresh']:
                        category_count = PerformanceResult.objects.filter(
                            mix__dataset=dataset,
                            category=category
                        ).count()
                        
                        validation_results['details'][f'{category}_results_count'] = category_count
                        logger.info(f"Found {category_count} {category} performance results")
                    
                    # Check if all mixes have at least one performance result
                    # Note: Using mix_id instead of id (Lesson learned: Primary Key Naming Conventions)
                    performance_result_mix_ids = PerformanceResult.objects.filter(
                        mix__dataset=dataset
                    ).values_list('mix__mix_id', flat=True)
                    
                    mixes_without_results = ConcreteMix.objects.filter(
                        dataset=dataset
                    ).exclude(
                        mix_id__in=performance_result_mix_ids
                    ).values_list('mix_code', flat=True)
                    
                    if mixes_without_results:
                        validation_results['warnings'].append(
                            f"{len(mixes_without_results)} mixes have no performance results: {list(mixes_without_results)}"
                        )
            
            # Check water-binder ratios
            # Improved validation with more specific error messages
            if dataset:
                w_b_ratio_issues = {
                    'too_low': [],
                    'too_high': [],
                    'missing': []
                }
                
                # Mixes with suspiciously low w/b ratios
                low_wb_mixes = ConcreteMix.objects.filter(
                    dataset=dataset,
                    w_b_ratio__lt=0.2,
                    w_b_ratio__gt=0  # Ensure not null or zero
                ).values_list('mix_code', 'w_b_ratio')
                
                for mix_code, ratio in low_wb_mixes:
                    w_b_ratio_issues['too_low'].append(f"{mix_code} ({ratio:.2f})")
                
                # Mixes with suspiciously high w/b ratios
                high_wb_mixes = ConcreteMix.objects.filter(
                    dataset=dataset,
                    w_b_ratio__gt=1.0
                ).values_list('mix_code', 'w_b_ratio')
                
                for mix_code, ratio in high_wb_mixes:
                    w_b_ratio_issues['too_high'].append(f"{mix_code} ({ratio:.2f})")
                
                # Mixes missing w/b ratios
                missing_wb_mixes = ConcreteMix.objects.filter(
                    dataset=dataset,
                    w_b_ratio__isnull=True
                ).values_list('mix_code', flat=True)
                
                if missing_wb_mixes:
                    w_b_ratio_issues['missing'] = list(missing_wb_mixes)
                
                # Report issues
                if w_b_ratio_issues['too_low']:
                    validation_results['issues'].append(
                        f"{len(w_b_ratio_issues['too_low'])} mixes have unusually low w/b ratios: {w_b_ratio_issues['too_low']}"
                    )
                    validation_results['success'] = False
                
                if w_b_ratio_issues['too_high']:
                    validation_results['issues'].append(
                        f"{len(w_b_ratio_issues['too_high'])} mixes have unusually high w/b ratios: {w_b_ratio_issues['too_high']}"
                    )
                    validation_results['success'] = False
                
                if w_b_ratio_issues['missing']:
                    validation_results['warnings'].append(
                        f"{len(w_b_ratio_issues['missing'])} mixes are missing w/b ratios: {w_b_ratio_issues['missing']}"
                    )
            
            # Log validation results
            if validation_results['success']:
                logger.info("Validation successful")
                self.update_status("Validation", "Import validation successful")
            else:
                logger.warning(f"Validation found issues: {validation_results['issues']}")
                self.update_status("Validation", 
                                   f"Import validation found {len(validation_results['issues'])} issues",
                                   True)
                self.stats['issues'].extend(validation_results['issues'])
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate import results: {str(e)}")
            self.update_status("Validation", f"Failed to validate: {str(e)}", True)
            self.stats['issues'].append(f"Validation failed: {str(e)}")
            validation_results['success'] = False
            validation_results['issues'].append(str(e))
            return validation_results

    def run(self):
        """Run the test import sequence."""
        logger.info("Starting Test Import Sequence for Phase 3 of Database Refresh Plan")
        self.update_status("Start", "Starting Test Import Sequence")
        
        # Initialize stats with more detailed tracking
        self.stats['phases'] = {
            'reference_tables': {'status': 'pending', 'duration': 0},
            'dataset_import': {'status': 'pending', 'duration': 0},
            'validation': {'status': 'pending', 'duration': 0},
            'performance': {'status': 'pending', 'duration': 0}
        }
        
        # Step 1: Import reference tables
        phase_start = datetime.datetime.now()
        logger.info("PHASE 1: Importing reference tables...")
        reference_success = self.import_reference_tables()
        phase_duration = (datetime.datetime.now() - phase_start).total_seconds()
        self.stats['phases']['reference_tables'] = {
            'status': 'success' if reference_success else 'failed',
            'duration': phase_duration
        }
        
        if not reference_success:
            logger.error("Reference tables import failed, aborting sequence")
            self.update_status("Complete", "Test Import Sequence aborted due to reference table import failure", True)
            return self.stats
        
        # Step 2: Import test dataset
        phase_start = datetime.datetime.now()
        logger.info("PHASE 2: Importing test dataset...")
        
        # Check if test_dataset.csv exists, use relative path to current file
        dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etl', 'test_dataset.csv')
        
        if not os.path.exists(dataset_path):
            logger.warning(f"Test dataset not found at: {dataset_path}")
            # Try alternative locations
            alternative_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_export', 'test_dataset.csv'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_dataset.csv')
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    dataset_path = alt_path
                    logger.info(f"Found test dataset at alternative location: {dataset_path}")
                    break
            else:
                error_msg = "Could not find test_dataset.csv in any expected locations"
                logger.error(error_msg)
                self.stats['issues'].append(error_msg)
                self.update_status("Dataset Import", error_msg, True)
                self.stats['phases']['dataset_import'] = {'status': 'failed', 'duration': 0}
                
                # Skip to validation with existing data if any
                logger.info("Skipping to validation with any existing data...")
                dataset_success = False
        
        # Import the dataset if we have a valid path
        if os.path.exists(dataset_path):
            dataset_success = self.import_test_dataset('TEST_DS', dataset_path)
        else:
            dataset_success = False
        
        phase_duration = (datetime.datetime.now() - phase_start).total_seconds()
        self.stats['phases']['dataset_import'] = {
            'status': 'success' if dataset_success else 'failed',
            'duration': phase_duration
        }
        
        if not dataset_success:
            logger.warning("Test dataset import failed or skipped, continuing with validation")
        
        # Step 3: Validate import results
        phase_start = datetime.datetime.now()
        logger.info("PHASE 3: Validating import results...")
        validation_results = self.validate_import_results()
        phase_duration = (datetime.datetime.now() - phase_start).total_seconds()
        
        self.stats['phases']['validation'] = {
            'status': 'success' if validation_results.get('success', False) else 'partial' if dataset_success else 'failed',
            'duration': phase_duration,
            'details': validation_results
        }
        
        # Step 4: Performance Testing (if dataset import was successful)
        if dataset_success:
            phase_start = datetime.datetime.now()
            logger.info("PHASE 4: Running performance tests...")
            performance_results = self.performance_test_import(dataset_path)
            phase_duration = (datetime.datetime.now() - phase_start).total_seconds()
            
            self.stats['phases']['performance'] = {
                'status': 'success' if performance_results.get('success', False) else 'partial',
                'duration': phase_duration,
                'details': performance_results
            }
        else:
            logger.warning("Skipping performance testing due to failed dataset import")
            self.stats['phases']['performance'] = {'status': 'skipped', 'duration': 0}
        
        # Complete the sequence with more detailed reporting
        total_duration = datetime.datetime.now() - self.start_time
        total_issues = len(self.stats['issues'])
        
        # Generate a summary of phases
        phase_summary = []
        for phase_name, phase_data in self.stats['phases'].items():
            phase_summary.append(f"{phase_name.replace('_', ' ').title()}: {phase_data['status'].upper()} in {phase_data.get('duration', 0):.1f}s")
        
        # Generate final message with comprehensive details
        completion_message = (
            f"Test Import Sequence completed in {total_duration.total_seconds():.1f} seconds. "
            f"Found {total_issues} issues.\n"
            f"Phase summary: {', '.join(phase_summary)}"
        )
        
        logger.info(completion_message)
        self.update_status("Complete", completion_message, total_issues > 0)
        
        # Document issues encountered (part of Test Import Sequence requirements)
        if self.stats['issues']:
            issues_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_import_issues.log')
            try:
                with open(issues_file, 'w') as f:
                    f.write(f"Test Import Issues - {datetime.datetime.now()}\n\n")
                    for idx, issue in enumerate(self.stats['issues'], 1):
                        f.write(f"{idx}. {issue}\n")
                logger.info(f"Documented {len(self.stats['issues'])} issues to {issues_file}")
            except Exception as e:
                logger.error(f"Failed to write issues log: {str(e)}")
        
        return self.stats

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Test Import Sequence for Phase 3 of Database Refresh Plan')
    parser.add_argument('--dataset', '-d', type=str, help='Path to the test dataset CSV file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--skip-performance', action='store_true', help='Skip performance testing phase')
    
    args = parser.parse_args()
    
    # Set up more detailed logging if verbose mode is enabled
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        # Add a more verbose file handler
        verbose_handler = logging.FileHandler('test_import_verbose.log')
        verbose_handler.setLevel(logging.DEBUG)
        verbose_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(verbose_handler)
        
        print("Verbose logging enabled - check test_import_verbose.log for detailed logs")
    
    print("===================================================================")
    print("Starting Test Import Sequence for Phase 3: Test Migration")
    print("===================================================================")
    print(f"Starting at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nRunning with settings:")
    print(f"  - Dataset path: {args.dataset if args.dataset else 'Using default search paths'}")
    
    # Create and run the test sequence
    test_sequence = TestImportSequence()
    
    if args.skip_performance:
        # Monkey patch the performance_test_import method to do nothing
        test_sequence.performance_test_import = lambda x: {'success': True, 'metrics': [], 'issues': []}
    
    # Set a custom dataset path if provided
    if args.dataset:
        # Store the original run method
        original_run = test_sequence.run
        
        # Define a wrapper to override the dataset path
        def run_with_custom_dataset():
            # Override the dataset path in the run method
            original_dataset_path = test_sequence.import_test_dataset
            
            def custom_import_dataset(dataset_code, _):
                return original_dataset_path(dataset_code, args.dataset)
            
            test_sequence.import_test_dataset = custom_import_dataset
            return original_run()
        
        # Replace the run method with our wrapper
        test_sequence.run = run_with_custom_dataset
    
    # Run the test sequence
    stats = test_sequence.run()
    
    print("\n===================================================================")
    print("Test Import Sequence Complete")
    print("===================================================================")
    
    # Print phase summary
    print("\nPhase summary:")
    print("--------------")
    for phase_name, phase_data in stats['phases'].items():
        phase_display = phase_name.replace('_', ' ').title()
        status_display = phase_data['status'].upper()
        duration = phase_data.get('duration', 0)
        
        # Color coding for status (using ANSI escape codes)
        status_color = ''
        if phase_data['status'] == 'success':
            status_color = '\033[92m'  # Green
        elif phase_data['status'] == 'failed':
            status_color = '\033[91m'  # Red
        elif phase_data['status'] in ['partial', 'pending']:
            status_color = '\033[93m'  # Yellow
        elif phase_data['status'] == 'skipped':
            status_color = '\033[94m'  # Blue
        
        reset_color = '\033[0m'
        
        print(f"{phase_display:20} | {status_color}{status_display:10}{reset_color} | {duration:.2f} seconds")
    
    # Print statistics
    print("\nImport statistics:")
    print("-----------------")
    print(f"Reference tables: {stats['reference_tables_imported']}")
    print(f"Reference records: {stats['reference_records_created']}")
    print(f"Dataset imported: {'Yes' if stats['dataset_imported'] else 'No'}")
    print(f"Mixes imported: {stats['mixes_imported']}")
    print(f"Components imported: {stats['components_imported']}")
    print(f"Results imported: {stats['results_imported']}")
    
    # Performance metrics if available
    if 'performance' in stats:
        print("\nPerformance metrics:")
        print("-------------------")
        for metric, value in stats['performance'].items():
            if isinstance(value, float):
                print(f"{metric}: {value:.2f}")
            else:
                print(f"{metric}: {value}")
    
    # Issues
    if stats['issues']:
        print("\nIssues encountered:")
        print("-------------------")
        for idx, issue in enumerate(stats['issues'], 1):
            print(f"{idx}. {issue}")
        print(f"\nDetailed issues have been saved to: test_import_issues.log")
    else:
        print("\nNo issues encountered. Test import sequence was successful!")
    
    # Final runtime
    runtime = datetime.datetime.now() - test_sequence.start_time
    print(f"\nTotal runtime: {runtime.total_seconds():.2f} seconds")
    
    # Next steps
    print("\n===================================================================")
    print("Next steps in the Database Refresh Plan:")
    print("===================================================================")
    print("1. Review any issues in test_import_issues.log")
    print("2. Proceed to 'Validation Run' to execute validation scripts")
    print("3. Fix any identified issues with the import scripts")
    print("4. Continue with 'Performance Testing' to establish expected timelines")
    print("\nYou can now proceed to the next step in the Database Refresh Plan.")
