#!/usr/bin/env python
"""
Performance Testing for Phase 3 of the Database Refresh Plan.

This script performs comprehensive performance testing of the ETL import process:
1. Measures time required for imports of different dataset sizes
2. Identifies performance bottlenecks in the ETL process
3. Establishes expected timelines for the production refresh
4. Generates performance reports and recommendations

Run this on the staging database to determine expected production performance.
"""
import os
import sys
import time
import logging
import datetime
import pandas as pd
import json
import argparse
import psutil
import random
import statistics
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')

import django
django.setup()

from django.db import transaction, connection, reset_queries
from django.db.models import Count, Q, F, Sum, Avg, Min, Max
from django.conf import settings
from refresh_status.models import DatabaseStatus, RefreshLogEntry

# Import models and importers
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
        logging.FileHandler('performance_testing.log')
    ]
)
logger = logging.getLogger('performance_testing')


class PerformanceMetrics:
    """Class to track performance metrics during import operations."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.dataset_size = 0
        self.num_mixes = 0
        self.num_components = 0
        self.num_results = 0
        self.memory_start = 0
        self.memory_peak = 0
        self.memory_end = 0
        self.memory_diff = 0
        self.queries_executed = 0
        self.db_operation_breakdown = {}
        self.dataset_name = None
    
    def start(self):
        """Start the performance timer and record baseline metrics."""
        self.start_time = time.time()
        self.memory_start = self._get_memory_usage()
        self.memory_peak = self.memory_start
        # Enable query counting if DEBUG is True
        if settings.DEBUG:
            reset_queries()
        logger.info(f"Starting performance test: {self.test_name}")
        logger.info(f"Initial memory usage: {self.memory_start:.2f} MB")
        
    def stop(self):
        """Stop the timer and calculate performance metrics."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.memory_end = self._get_memory_usage()
        self.memory_diff = self.memory_end - self.memory_start
        
        # Count queries if DEBUG is True
        if settings.DEBUG:
            self.queries_executed = len(connection.queries)
            # Analyze query types
            self._analyze_query_types()
        
        logger.info(f"Completed performance test: {self.test_name}")
        logger.info(f"Duration: {self.duration:.2f} seconds")
        logger.info(f"Final memory usage: {self.memory_end:.2f} MB (Change: {self.memory_diff:.2f} MB)")
        logger.info(f"Peak memory usage: {self.memory_peak:.2f} MB")
        if settings.DEBUG:
            logger.info(f"Database queries executed: {self.queries_executed}")
        
    def record_dataset_stats(self, dataset_name: str, mixes: int, components: int, results: int):
        """Record statistics about the imported dataset."""
        self.dataset_name = dataset_name
        self.num_mixes = mixes
        self.num_components = components
        self.num_results = results
        self.dataset_size = mixes + components + results
        
    def update_peak_memory(self):
        """Update the peak memory usage if current usage is higher."""
        current = self._get_memory_usage()
        if current > self.memory_peak:
            self.memory_peak = current
        
    def _get_memory_usage(self) -> float:
        """Get the current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)  # Convert to MB
    
    def _analyze_query_types(self):
        """Analyze database queries by type (SELECT, INSERT, UPDATE, etc.)."""
        if not settings.DEBUG or not hasattr(connection, 'queries'):
            return
            
        query_types = {}
        for query_info in connection.queries:
            query = query_info['sql'].strip().upper()
            query_type = query.split()[0] if query else 'UNKNOWN'
            
            if query_type not in query_types:
                query_types[query_type] = 0
            query_types[query_type] += 1
            
        self.db_operation_breakdown = query_types
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        # Safely calculate derived metrics to avoid division by zero
        entities_per_second = 0
        if self.duration and self.duration > 0 and self.dataset_size > 0:
            entities_per_second = self.dataset_size / self.duration
            
        mb_per_entity = 0
        if self.dataset_size and self.dataset_size > 0:
            mb_per_entity = self.memory_diff / self.dataset_size
            
        return {
            'test_name': self.test_name,
            'dataset_name': self.dataset_name,
            'dataset_size': self.dataset_size,
            'num_mixes': self.num_mixes,
            'num_components': self.num_components,
            'num_results': self.num_results,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': self.duration,
            'memory_start_mb': self.memory_start,
            'memory_end_mb': self.memory_end,
            'memory_diff_mb': self.memory_diff,
            'memory_peak_mb': self.memory_peak,
            'queries_executed': self.queries_executed,
            'db_operation_breakdown': self.db_operation_breakdown,
            'entities_per_second': entities_per_second,
            'mb_per_entity': mb_per_entity
        }


class TestDataGenerator:
    """Class to generate test datasets of varying sizes for performance testing."""
    
    def __init__(self, base_size: int = 5):
        self.base_size = base_size
        self.material_classes = self._ensure_material_classes()
        self.units = self._ensure_units()
        self.test_methods = self._ensure_test_methods()
        self.standards = self._ensure_standards()
        self.property_dict = self._ensure_property_dictionary()
        
    def _ensure_material_classes(self) -> Dict[str, MaterialClass]:
        """Ensure essential material classes exist, create if needed."""
        essential_classes = [
            {'code': 'CEMENT', 'name': 'Cement'},
            {'code': 'WATER', 'name': 'Water'},
            {'code': 'AGGR_F', 'name': 'Fine Aggregate'},
            {'code': 'AGGR_C', 'name': 'Coarse Aggregate'},
            {'code': 'SCM', 'name': 'SCM'},
            {'code': 'ADMIX', 'name': 'Admixture'}
        ]
        class_dict = {}
        
        for class_info in essential_classes:
            mat_class, created = MaterialClass.objects.get_or_create(
                class_code=class_info['code'],
                defaults={'class_name': class_info['name']}
            )
            class_dict[class_info['name']] = mat_class
            if created:
                logger.info(f"Created missing material class: {class_info['name']}")
                
        return class_dict
    
    def _ensure_units(self) -> Dict[str, UnitLookup]:
        """Ensure essential units exist, create if needed."""
        essential_units = {
            'kg': 'Mass unit for material quantities',
            'm³': 'Volume unit for concrete',
            'MPa': 'Pressure unit for strength measurements',
            'mm': 'Length unit for dimensions',
            '%': 'Percentage unit for proportions',
            'days': 'Time unit for curing duration'
        }
        unit_dict = {}
        
        for unit_name, description in essential_units.items():
            unit, created = UnitLookup.objects.get_or_create(
                unit_symbol=unit_name, 
                defaults={'description': description}
            )
            unit_dict[unit_name] = unit
            if created:
                logger.info(f"Created missing unit: {unit_name} ({description})")
                
        return unit_dict
    
    def _ensure_test_methods(self) -> Dict[str, TestMethod]:
        """Ensure essential test methods exist, create if needed."""
        essential_methods = {
            'Compressive Strength': 'ASTM C39',
            'Slump': 'ASTM C143',
            'Air Content': 'ASTM C231'
        }
        method_dict = {}
        
        for method_name, standard_code in essential_methods.items():
            # First get or create the standard
            try:
                standard, std_created = Standard.objects.get_or_create(
                    code=standard_code,
                    defaults={'title': f'Standard Test Method for {method_name}'}
                )
                
                # Then get or create the test method
                method, created = TestMethod.objects.get_or_create(
                    description=method_name,
                    defaults={'standard': standard}
                )
                method_dict[method_name] = method
                
                if created:
                    logger.info(f"Created missing test method: {method_name}")
                if std_created:
                    logger.info(f"Created missing standard: {standard_code}")
                    
            except Exception as e:
                logger.warning(f"Error creating test method {method_name}: {str(e)}")
                # Try to find existing method by description only
                try:
                    method = TestMethod.objects.filter(description__icontains=method_name).first()
                    if method:
                        method_dict[method_name] = method
                        logger.info(f"Found existing test method for {method_name}")
                except Exception as inner_e:
                    logger.error(f"Could not find fallback test method: {str(inner_e)}")
                
        return method_dict
    
    def _ensure_standards(self) -> Dict[str, Standard]:
        """Ensure essential standards exist, create if needed."""
        essential_standards = ['ASTM C39', 'ASTM C143', 'ASTM C231']
        standards_dict = {}
        
        for std_code in essential_standards:
            standard, created = Standard.objects.get_or_create(
                code=std_code,
                defaults={'title': f"Standard Test Method {std_code}"}
            )
            standards_dict[std_code] = standard
            if created:
                logger.info(f"Created missing standard: {std_code}")
                
        return standards_dict
    
    def _ensure_property_dictionary(self) -> Dict[str, PropertyDictionary]:
        """Ensure essential property dictionary entries exist, create if needed."""
        essential_properties = {
            'compressive_strength': {'display_name': 'Compressive Strength', 'unit': 'MPa', 'group': 'mechanical'},
            'slump': {'display_name': 'Slump', 'unit': 'mm', 'group': 'physical'},
            'air_content': {'display_name': 'Air Content', 'unit': '%', 'group': 'physical'}
        }
        property_dict = {}
        
        for prop_name, prop_data in essential_properties.items():
            try:
                # Look for existing property first
                prop = PropertyDictionary.objects.get(property_name=prop_name)
                property_dict[prop_name] = prop
                logger.debug(f"Found existing property: {prop_name}")
            except PropertyDictionary.DoesNotExist:
                # Create only if not exists
                try:
                    unit = self.units[prop_data['unit']]
                    prop = PropertyDictionary.objects.create(
                        property_name=prop_name,
                        display_name=prop_data['display_name'],
                        property_group=prop_data['group'],
                        default_unit=unit
                    )
                    property_dict[prop_name] = prop
                    logger.info(f"Created missing property dictionary entry: {prop_name}")
                except Exception as e:
                    logger.warning(f"Could not create property {prop_name}: {str(e)}")
                    # Try to get it without unit if creation fails
                    try:
                        prop = PropertyDictionary.objects.get(property_name=prop_name)
                        property_dict[prop_name] = prop
                    except PropertyDictionary.DoesNotExist:
                        logger.error(f"Could not find or create property: {prop_name}")
                
        return property_dict
        
    def create_test_dataset(self, size_multiplier: int = 1, name_prefix: str = 'PERF_TEST') -> Tuple[Dataset, pd.DataFrame]:
        """Create a test dataset with the specified size for performance testing.
        
        Args:
            size_multiplier: Multiplier for base size to control dataset size
            name_prefix: Prefix for the dataset name
            
        Returns:
            Tuple of (Dataset object, DataFrame with dataset contents)
        """
        # Calculate actual size based on multiplier
        num_mixes = self.base_size * size_multiplier
        logger.info(f"Creating test dataset with {num_mixes} mixes (size multiplier: {size_multiplier})")
        
        # Create dataset with unique name
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dataset_name = f"{name_prefix}_{size_multiplier}x_{timestamp}"
        
        # Create dataset using only the fields that exist in the model
        dataset = Dataset.objects.create(
            dataset_name=dataset_name,
            license=f"Performance test dataset with {num_mixes} mixes for benchmark testing only"
        )
        
        # Create dataframe for the dataset
        data = []
        for i in range(num_mixes):
            # Create mix data with EXACT column names expected by TestDatasetImporter
            # Based on examining test_dataset_importer.py extract_mix_components method
            mix_data = {
                'mix_code': f"mix{i}",  # Keep simple as dataset name will be prefixed
                'strength_class': random.choice(['C20', 'C25', 'C30', 'C35', 'C40', 'C45', 'C50']),
                'description': f"Test mix {i} for performance testing",
                'w_c_ratio': round(random.uniform(0.35, 0.55), 2),
                'w_b_ratio': round(random.uniform(0.35, 0.50), 2),
            }
            
            # Add cement (always present) - EXACTLY matching the expected column names
            cement_qty = round(random.uniform(300, 450), 1)
            mix_data['cement'] = cement_qty  # This is the exact column name expected in extract_mix_components
            
            # Add water - match w/c ratio (EXACT column name expected by the importer)
            mix_data['water'] = round(cement_qty * mix_data['w_c_ratio'], 1)
            
            # Add fine aggregate (EXACT column name expected by the importer)
            mix_data['fine_aggregate'] = round(random.uniform(700, 900), 1)
            
            # Add coarse aggregate (EXACT column name expected by the importer)
            mix_data['coarse_aggregate'] = round(random.uniform(900, 1200), 1)
            
            # Add SCM - fly ash (sometimes present) - EXACT column name expected by the importer
            if random.random() > 0.5:
                mix_data['fly_ash'] = round(random.uniform(50, 100), 1)
                
            # Add silica fume (sometimes present) - EXACT column name expected by the importer
            if random.random() > 0.7:
                mix_data['silica_fume'] = round(random.uniform(20, 50), 1)
                
            # Add superplasticizer (sometimes present) - EXACT column name expected by the importer
            if random.random() > 0.6:
                mix_data['superplasticizer'] = round(random.uniform(2, 10), 1)
                
            # Add performance results (using column names that should be recognized)
            mix_data['slump'] = round(random.uniform(50, 200), 0)
            mix_data['air_content'] = round(random.uniform(1.5, 6.0), 1)
            mix_data['compressive_strength'] = round(random.uniform(20, 60), 1)
            mix_data['age_days'] = 28
            
            data.append(mix_data)
            
        # Create DataFrame
        df = pd.DataFrame(data)
        
        logger.info(f"Created test dataset '{dataset_name}' with {len(df)} rows")
        return dataset, df
    
    def save_dataset_to_csv(self, df: pd.DataFrame, dataset_name: str) -> str:
        """Save dataset DataFrame to CSV file.
        
        Args:
            df: DataFrame with dataset contents
            dataset_name: Name of the dataset
            
        Returns:
            Path to the saved CSV file
        """
        csv_path = Path(f"{dataset_name}.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved test dataset to {csv_path}")
        return str(csv_path)


class PerformanceTester:
    """Main class for running performance tests on the ETL import process."""
    
    def __init__(self, cleanup: bool = True):
        """Initialize the performance tester.
        
        Args:
            cleanup: Whether to clean up test datasets after testing
        """
        self.cleanup = cleanup
        self.test_generator = TestDataGenerator()
        self.test_results = []
        self.test_datasets = []
        
    def prepare_test_datasets(self, sizes: List[int] = [1, 2, 5, 10]) -> List[Tuple[Dataset, str]]:
        """Prepare test datasets of various sizes for performance testing.
        
        Args:
            sizes: List of size multipliers for test datasets
            
        Returns:
            List of tuples (Dataset object, path to CSV file)
        """
        prepared_datasets = []
        
        for size in sizes:
            # Create dataset and save to CSV
            dataset, df = self.test_generator.create_test_dataset(size_multiplier=size)
            csv_path = self.test_generator.save_dataset_to_csv(df, dataset.dataset_name)
            
            prepared_datasets.append((dataset, csv_path))
            self.test_datasets.append(dataset)
            
        logger.info(f"Prepared {len(prepared_datasets)} test datasets for performance testing")
        return prepared_datasets
    
    def run_import_performance_test(self, dataset: Dataset, csv_path: str) -> Dict[str, Any]:
        """Run performance test for importing a dataset.
        
        Args:
            dataset: Dataset object to import
            csv_path: Path to the CSV file with dataset contents
            
        Returns:
            Dictionary with performance metrics
        """
        # Create performance metrics tracker
        metrics = PerformanceMetrics(f"Import {dataset.dataset_name}")
        
        try:
            # Start tracking performance
            metrics.start()
            
            # Use transaction to allow rollback if needed
            with transaction.atomic():
                # Create importer with required parameters
                importer = TestDatasetImporter(
                    dataset_code=dataset.dataset_name, 
                    csv_path=csv_path,
                    logger=logger
                )
                
                # First load the data - this step is required
                if importer.load_data():
                    # Run import process
                    success = importer.import_data()
                    
                    # Get stats from importer
                    import_result = {
                        'mixes_imported': importer.stats.get('mixes_imported', 0),
                        'components_imported': importer.stats.get('components_imported', 0),
                        'results_imported': importer.stats.get('results_imported', 0)
                    }
                else:
                    logger.error(f"Failed to load data from {csv_path}")
                    import_result = {
                        'mixes_imported': 0,
                        'components_imported': 0,
                        'results_imported': 0
                    }
                
                # Update peak memory after import
                metrics.update_peak_memory()
                
                # Record dataset statistics
                metrics.record_dataset_stats(
                    dataset_name=dataset.dataset_name,
                    mixes=import_result.get('mixes_imported', 0),
                    components=import_result.get('components_imported', 0),
                    results=import_result.get('results_imported', 0)
                )
                
            # Stop performance tracking
            metrics.stop()
            
            # Add metrics to results
            result = metrics.to_dict()
            self.test_results.append(result)
            
            return result
        
        except Exception as e:
            logger.error(f"Error during performance test for {dataset.dataset_name}: {str(e)}")
            # Stop metrics tracking even if import failed
            if metrics.start_time is not None:
                metrics.stop()
            
            return {
                'test_name': metrics.test_name,
                'dataset_name': dataset.dataset_name,
                'error': str(e),
                'duration_seconds': metrics.duration if metrics.duration else 0
            }
            
    def run_batch_test(self, sizes: List[int] = [1, 2, 5, 10], iterations: int = 1) -> List[Dict[str, Any]]:
        """Run batch performance test with multiple dataset sizes and iterations.
        
        Args:
            sizes: List of size multipliers for test datasets
            iterations: Number of iterations to run for each size
            
        Returns:
            List of dictionaries with performance metrics
        """
        logger.info(f"Starting batch performance test with sizes {sizes} and {iterations} iterations")
        
        all_results = []
        
        # Prepare datasets
        datasets = self.prepare_test_datasets(sizes=sizes)
        
        # Run tests for each dataset
        for dataset, csv_path in datasets:
            size_results = []
            
            # Run multiple iterations
            for i in range(iterations):
                logger.info(f"Running iteration {i+1}/{iterations} for dataset {dataset.dataset_name}")
                
                # Run test and store result
                result = self.run_import_performance_test(dataset, csv_path)
                size_results.append(result)
                
            # Calculate average for this size
            if size_results and all('error' not in r for r in size_results):
                avg_result = self._calculate_average_metrics(size_results)
                all_results.append(avg_result)
            else:
                # Just add the individual results if there were errors
                all_results.extend(size_results)
                
        return all_results
    
    def _calculate_average_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate average metrics across multiple test runs.
        
        Args:
            results: List of test result dictionaries
            
        Returns:
            Dictionary with average metrics
        """
        if not results:
            return {}
            
        # Use the first result as a template
        avg_result = results[0].copy()
        avg_result['test_name'] = f"Average for {avg_result['dataset_name']}"
        
        # Fields to average
        fields_to_avg = [
            'duration_seconds', 'memory_start_mb', 'memory_end_mb', 
            'memory_diff_mb', 'memory_peak_mb', 'queries_executed',
            'entities_per_second', 'mb_per_entity'
        ]
        
        # Calculate averages
        for field in fields_to_avg:
            if field in avg_result:
                values = [r.get(field, 0) for r in results if field in r]
                if values:
                    avg_result[field] = sum(values) / len(values)
                    
        # Add standard deviation for key metrics
        key_metrics = ['duration_seconds', 'entities_per_second', 'memory_peak_mb']
        for metric in key_metrics:
            if metric in avg_result:
                values = [r.get(metric, 0) for r in results if metric in r]
                if len(values) > 1:
                    avg_result[f"{metric}_std"] = statistics.stdev(values)
                else:
                    avg_result[f"{metric}_std"] = 0.0
                    
        return avg_result
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze performance test results and generate summary.
        
        Returns:
            Dictionary with analysis results
        """
        if not self.test_results:
            return {'error': 'No test results available'}
            
        # Extract results without errors
        valid_results = [r for r in self.test_results if 'error' not in r]
        if not valid_results:
            return {'error': 'No valid test results available'}
            
        # Calculate scaling factors
        size_to_duration = {}
        size_to_entities_per_second = {}
        
        for result in valid_results:
            # Extract size from dataset name (format: PERF_TEST_<SIZE>x_<TIMESTAMP>)
            dataset_name = result.get('dataset_name', '')
            size_parts = dataset_name.split('_')
            size = None
            
            for part in size_parts:
                if part.endswith('x'):
                    try:
                        size = int(part.rstrip('x'))
                        break
                    except ValueError:
                        pass
            
            if size is not None:
                duration_secs = result.get('duration_seconds', 0) or 0.001  # Avoid division by zero
                size_to_duration[size] = duration_secs
                size_to_entities_per_second[size] = result.get('entities_per_second', 0) or 0
                
        # Calculate scaling trend
        scaling_analysis = {}
        if len(size_to_duration) >= 2:
            try:
                # Sort sizes for trend analysis
                sorted_sizes = sorted(size_to_duration.keys())
                
                # Calculate linear scaling factor with safeguards
                smallest_size = sorted_sizes[0] or 1  # Avoid division by zero
                largest_size = sorted_sizes[-1] or 2  # Ensure different from smallest if zero
                
                smallest_duration = size_to_duration[smallest_size] or 0.001  # Avoid division by zero
                largest_duration = size_to_duration[largest_size] or 0.001  # Avoid division by zero
                
                size_ratio = largest_size / smallest_size
                time_ratio = largest_duration / smallest_duration
                
                scaling_analysis['size_ratio'] = size_ratio
                scaling_analysis['time_ratio'] = time_ratio
                
                # Safe division
                if size_ratio > 0:
                    scaling_analysis['scaling_factor'] = time_ratio / size_ratio
                else:
                    scaling_analysis['scaling_factor'] = 1.0  # Default to linear if can't calculate
                
                # Check if scaling is linear, superlinear, or sublinear
                if 0.9 <= scaling_analysis['scaling_factor'] <= 1.1:
                    scaling_analysis['scaling_type'] = 'linear'
                elif scaling_analysis['scaling_factor'] > 1.1:
                    scaling_analysis['scaling_type'] = 'superlinear'
                else:
                    scaling_analysis['scaling_type'] = 'sublinear'
                    
                # Calculate throughput stability (with safeguards)
                entity_rates = list(size_to_entities_per_second.values())
                if entity_rates:
                    scaling_analysis['min_entities_per_second'] = min(entity_rates)
                    scaling_analysis['max_entities_per_second'] = max(entity_rates)
                    
                    # Safe calculation of average
                    avg_rate = sum(entity_rates) / len(entity_rates) if entity_rates else 0
                    scaling_analysis['avg_entities_per_second'] = avg_rate
                    
                    # Calculate throughput variation (with safeguards)
                    if len(entity_rates) > 1 and avg_rate > 0:
                        scaling_analysis['throughput_variation'] = statistics.stdev(entity_rates) / avg_rate
                    else:
                        scaling_analysis['throughput_variation'] = 0.0
            except Exception as e:
                logger.warning(f"Error calculating scaling analysis: {str(e)}")
                scaling_analysis['error'] = str(e)
                scaling_analysis['scaling_type'] = 'unknown'
        
        # Estimate times for production-sized databases
        estimated_times = {}
        if valid_results:
            # Use the average entities per second from all tests (with safeguards)
            total_rate = sum(r.get('entities_per_second', 0) or 0 for r in valid_results)
            count = len(valid_results)
            avg_rate = total_rate / count if count > 0 else 0.001  # Avoid division by zero
            
            # Use a minimum processing rate to prevent unrealistic estimates
            avg_rate = max(avg_rate, 0.001)  # At least 0.001 entities per second
            
            # Estimate for various database sizes
            production_sizes = [1000, 5000, 10000, 50000, 100000]  # entities
            for size in production_sizes:
                # Always safe since avg_rate has minimum value
                estimated_times[size] = size / avg_rate  # seconds
                    
        # Identify potential bottlenecks
        bottlenecks = []
        
        # Check for query volume issues
        if any(r.get('queries_executed', 0) > 1000 for r in valid_results):
            bottlenecks.append({
                'type': 'database_queries',
                'description': 'High number of database queries detected - consider using bulk operations',
                'severity': 'medium'
            })
            
        # Check for memory usage issues
        if any(r.get('memory_peak_mb', 0) > 1000 for r in valid_results):
            bottlenecks.append({
                'type': 'memory_usage',
                'description': 'High memory usage detected - consider batch processing',
                'severity': 'high'
            })
            
        # Check for scaling issues
        if scaling_analysis.get('scaling_factor', 1.0) > 1.5:
            bottlenecks.append({
                'type': 'scaling',
                'description': 'Import time scales worse than linearly with dataset size',
                'severity': 'high'
            })
            
        # Prepare final analysis
        analysis = {
            'num_tests': len(self.test_results),
            'num_valid_tests': len(valid_results),
            'scaling_analysis': scaling_analysis,
            'estimated_times': estimated_times,
            'bottlenecks': bottlenecks,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        return analysis
    
    def generate_report(self, output_file: str = 'performance_report.json') -> str:
        """Generate performance report in JSON format.
        
        Args:
            output_file: Path to output file
            
        Returns:
            Path to the generated report file
        """
        # Prepare report data
        report = {
            'test_results': self.test_results,
            'analysis': self.analyze_results(),
            'timestamp': datetime.datetime.now().isoformat(),
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'cpu_count': os.cpu_count()
            }
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Performance report saved to {output_file}")
        return output_file
    
    def cleanup_test_data(self):
        """Clean up test datasets created during performance testing."""
        if not self.cleanup or not self.test_datasets:
            return
            
        logger.info(f"Cleaning up {len(self.test_datasets)} test datasets")
        
        for dataset in self.test_datasets:
            try:
                # Identify objects to delete
                mixes = ConcreteMix.objects.filter(dataset=dataset)
                components = MixComponent.objects.filter(mix__dataset=dataset)
                results = PerformanceResult.objects.filter(mix__dataset=dataset)
                
                # Delete in reverse order to avoid foreign key constraints
                logger.info(f"Deleting {results.count()} performance results for {dataset.dataset_name}")
                results.delete()
                
                logger.info(f"Deleting {components.count()} mix components for {dataset.dataset_name}")
                components.delete()
                
                logger.info(f"Deleting {mixes.count()} mixes for {dataset.dataset_name}")
                mixes.delete()
                
                # Delete dataset itself
                dataset.delete()
                logger.info(f"Deleted dataset {dataset.dataset_name}")
                
                # Delete CSV file if it exists
                csv_path = Path(f"{dataset.dataset_name}.csv")
                if csv_path.exists():
                    csv_path.unlink()
                    logger.info(f"Deleted CSV file {csv_path}")
                    
            except Exception as e:
                logger.error(f"Error cleaning up dataset {dataset.dataset_name}: {str(e)}")
                
        self.test_datasets = []


def update_refresh_status(status_message: str):
    """Update the database status with performance testing information."""
    try:
        # Make sure status message fits within the field constraints (max 20 chars)
        short_status = status_message[:18] + '..' if len(status_message) > 20 else status_message
        
        # Use one of the predefined statuses instead of custom message
        db_status = DatabaseStatus.IN_PROGRESS
        
        # Update the database status
        status, created = DatabaseStatus.objects.get_or_create(
            pk=1,
            defaults={
                'status': db_status,
                'last_updated': datetime.datetime.now(),
                'current_phase': 'Performance Testing',
                'current_step': short_status
            }
        )
        
        if not created:
            status.status = db_status
            status.last_updated = datetime.datetime.now()
            status.current_phase = 'Performance Testing'
            status.current_step = short_status
            status.save()
            
        # Create log entry with proper fields from the model
        RefreshLogEntry.objects.create(
            phase='Performance Testing',
            step='Database Import Benchmarking',
            status=db_status,
            message=status_message,  # Full message can be stored here
            is_error=False,
            details={'type': 'performance_test'}
        )
        
        logger.info(f"Updated database status: {short_status}")
        
    except Exception as e:
        logger.error(f"Error updating database status: {str(e)}")
        # Try to continue even if status update fails


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Performance testing for ETL import process')
    
    parser.add_argument('--sizes', type=int, nargs='+', default=[1, 2, 5, 10],
                        help='Size multipliers for test datasets')
    parser.add_argument('--iterations', type=int, default=1,
                        help='Number of iterations to run for each dataset size')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='Do not clean up test datasets after testing')
    parser.add_argument('--output', type=str, default='performance_report.json',
                        help='Path to output report file')
    parser.add_argument('--base-size', type=int, default=5,
                        help='Base size for test datasets (number of mixes)')
    
    return parser.parse_args()


def main():
    """Main entry point for performance testing."""
    # Parse command line arguments
    args = parse_arguments()
    
    logger.info("====================================================================")
    logger.info("Starting Performance Testing for Phase 3: Test Migration")
    logger.info("====================================================================")
    logger.info(f"Starting at: {datetime.datetime.now()}")
    logger.info(f"Testing dataset sizes: {args.sizes} with {args.iterations} iterations each")
    logger.info(f"Base size: {args.base_size} mixes per dataset")
    
    # Update database status - limit message length to fit in the field
    status_message = f"Perf testing: {args.sizes} x {args.iterations}"
    update_refresh_status(status_message)
    
    # Start performance testing
    start_time = time.time()
    
    try:
        # Create performance tester
        tester = PerformanceTester(cleanup=not args.no_cleanup)
        
        # Run batch test
        tester.run_batch_test(sizes=args.sizes, iterations=args.iterations)
        
        # Generate report
        report_path = tester.generate_report(output_file=args.output)
        
        # Analyze results
        analysis = tester.analyze_results()
        
        # Display summary
        logger.info("\n====================================================================")
        logger.info("Performance Testing Complete")
        logger.info("====================================================================\n")
        
        logger.info("Performance Summary:")
        logger.info("-----------------")
        logger.info(f"Tests run: {analysis.get('num_tests', 0)}")
        logger.info(f"Valid tests: {analysis.get('num_valid_tests', 0)}")
        
        scaling = analysis.get('scaling_analysis', {})
        if scaling:
            logger.info(f"Scaling type: {scaling.get('scaling_type', 'unknown')}")
            logger.info(f"Average throughput: {scaling.get('avg_entities_per_second', 0):.2f} entities/second")
            
        # Display estimated times for production
        estimated = analysis.get('estimated_times', {})
        if estimated:
            logger.info("\nEstimated Import Times for Production:")
            logger.info("---------------------------------")
            for size, seconds in sorted(estimated.items()):
                minutes = seconds / 60
                hours = minutes / 60
                
                if hours >= 1:
                    logger.info(f"{size} entities: {hours:.2f} hours")
                elif minutes >= 1:
                    logger.info(f"{size} entities: {minutes:.2f} minutes")
                else:
                    logger.info(f"{size} entities: {seconds:.2f} seconds")
                    
        # Display bottlenecks
        bottlenecks = analysis.get('bottlenecks', [])
        if bottlenecks:
            logger.info("\nPotential Bottlenecks:")
            logger.info("---------------------")
            for bottleneck in bottlenecks:
                logger.info(f"[{bottleneck.get('severity', 'unknown').upper()}] {bottleneck.get('description', '')}")
                
        # Clean up if requested
        if not args.no_cleanup:
            tester.cleanup_test_data()
            
        # Calculate total runtime
        runtime = time.time() - start_time
        logger.info(f"\nTotal runtime: {runtime:.2f} seconds")
        
        # Update database status - keep message short to fit field constraints
        status_message = f"Perf test complete: {runtime:.2f}s"
        update_refresh_status(status_message)
        
        logger.info("\nPerformance report saved to: {}".format(report_path))
        logger.info("\n====================================================================")
        
    except Exception as e:
        logger.error(f"Error during performance testing: {str(e)}")
        status_message = f"Performance testing failed: {str(e)}"
        update_refresh_status(status_message)
        

if __name__ == '__main__':
    main()
