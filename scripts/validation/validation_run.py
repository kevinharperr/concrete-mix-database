#!/usr/bin/env python
"""
Validation Run for Phase 3 of the Database Refresh Plan.

This script performs comprehensive validation of imported data, focusing on:
1. Component relationships (cement, water, aggregates)
2. Calculated values (w/c ratio, w/b ratio)
3. Performance result consistency and completeness
4. Cross-dataset relationship validation

Run this on the staging database after test import sequence is completed.
"""
import os
import sys
import logging
import datetime
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import json
import argparse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')

import django
django.setup()

from django.db import transaction, connection
from django.db.models import Count, Q, F, Sum, Avg, Min, Max
from django.core.exceptions import ValidationError
from refresh_status.models import DatabaseStatus, RefreshLogEntry

# Import models
from cdb_app.models import (
    Dataset, Material, MaterialClass, UnitLookup, PropertyDictionary,
    ConcreteMix, MixComponent, PerformanceResult, TestMethod, Standard
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('validation_run.log')
    ]
)
logger = logging.getLogger('validation_run')

class ValidationRun:
    """Manages the validation run for the database refresh."""
    
    def __init__(self, target_datasets=None):
        """Initialize the validation run.
        
        Args:
            target_datasets: Optional list of dataset codes to validate
                            If None, validates all datasets in the database
        """
        self.target_datasets = target_datasets
        self.stats = {
            'datasets_validated': 0,
            'mixes_validated': 0,
            'components_validated': 0,
            'results_validated': 0,
            'validation_warnings': [],
            'validation_errors': [],
            'w_c_ratio_stats': {},
            'w_b_ratio_stats': {},
            'performance_result_stats': {}
        }
        self.start_time = datetime.datetime.now()
        
        # Thresholds for validation warnings and errors
        self.thresholds = {
            'w_c_ratio': {'min': 0.25, 'max': 0.90},
            'w_b_ratio': {'min': 0.20, 'max': 0.80},
            'compressive_strength': {'min': 5.0, 'max': 120.0},  # MPa
            'slump': {'min': 0.0, 'max': 300.0}  # mm
        }
        
        # Material class mappings - used to identify component types
        self.material_classes = self._load_material_classes()
    
    def _load_material_classes(self) -> Dict[str, int]:
        """Load material classes from the database into a mapping.
        
        Returns:
            Dictionary mapping material type names to material class IDs
        """
        material_class_map = {}
        try:
            # Using Django's model introspection to verify field existence
            material_class_fields = [f.name for f in MaterialClass._meta.get_fields()]
            
            # Get primary key field name (lesson learned: not always 'id')
            pk_field = MaterialClass._meta.pk.name
            logger.info(f"MaterialClass primary key field: {pk_field}")
            
            # Only proceed if we have the expected fields
            if 'name' in material_class_fields:
                for mc in MaterialClass.objects.all():
                    # Get the primary key value regardless of field name
                    pk_value = getattr(mc, pk_field)
                    # Create case-insensitive mapping
                    material_class_map[mc.name.lower()] = pk_value
                
                logger.info(f"Loaded {len(material_class_map)} material classes")
            else:
                logger.warning("MaterialClass model missing 'name' field. Component validation may be limited.")
                
        except Exception as e:
            logger.error(f"Error loading material classes: {str(e)}")
        
        return material_class_map
    
    def update_status(self, step: str, message: str, is_error: bool = False):
        """Update the database status and log an entry."""
        try:
            # Get current status
            status = DatabaseStatus.objects.latest('last_updated')
            
            # Create log entry
            RefreshLogEntry.objects.create(
                phase="Phase 3: Validation Run",
                step=step,
                status="error" if is_error else "info",
                message=message,
                is_error=is_error
            )
            
            # Update status details
            status.current_step = f"Validation: {step}"
            status.progress_percentage = 50  # Adjust based on progress
            if is_error:
                status.error_message = message
            status.save()
            
            logger.info(f"Status updated: {message}")
            
        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}")
    
    def validate_datasets(self) -> Dict[str, Any]:
        """Validate all target datasets or all datasets in the database."""
        logger.info("Starting dataset validation")
        self.update_status("Datasets", "Starting dataset validation")
        
        validation_results = {
            'success': True,
            'dataset_results': {}
        }
        
        try:
            # Get datasets to validate
            if self.target_datasets:
                datasets = Dataset.objects.filter(dataset_name__in=self.target_datasets)
            else:
                datasets = Dataset.objects.all()
            
            if not datasets.exists():
                msg = "No datasets found for validation"
                logger.warning(msg)
                self.stats['validation_warnings'].append(msg)
                return {
                    'success': False,
                    'error': msg
                }
            
            # Validate each dataset
            for dataset in datasets:
                logger.info(f"Validating dataset: {dataset.dataset_name}")
                dataset_result = self.validate_single_dataset(dataset)
                validation_results['dataset_results'][dataset.dataset_name] = dataset_result
                
                if not dataset_result.get('success', False):
                    validation_results['success'] = False
                
                self.stats['datasets_validated'] += 1
            
            return validation_results
                
        except Exception as e:
            logger.error(f"Dataset validation failed: {str(e)}")
            self.update_status("Datasets", f"Dataset validation failed: {str(e)}", True)
            self.stats['validation_errors'].append(f"Dataset validation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_single_dataset(self, dataset: Dataset) -> Dict[str, Any]:
        """Validate a single dataset including its mixes, components, and results."""
        dataset_stats = {
            'dataset_name': dataset.dataset_name,
            'mixes_count': 0,
            'components_count': 0,
            'results_count': 0,
            'issues': [],
            'warnings': [],
            'success': True
        }
        
        try:
            # Validate mixes
            mix_validation = self.validate_mixes(dataset)
            dataset_stats.update(mix_validation)
            
            # Validate components
            component_validation = self.validate_components(dataset)
            dataset_stats.update(component_validation)
            
            # Validate performance results
            result_validation = self.validate_performance_results(dataset)
            dataset_stats.update(result_validation)
            
            # Check if we found any critical issues
            if len(dataset_stats['issues']) > 0:
                dataset_stats['success'] = False
            
            return dataset_stats
            
        except Exception as e:
            logger.error(f"Failed to validate dataset {dataset.dataset_name}: {str(e)}")
            dataset_stats['issues'].append(f"Validation error: {str(e)}")
            dataset_stats['success'] = False
            return dataset_stats
    
    def validate_mixes(self, dataset: Dataset) -> Dict[str, Any]:
        """Validate concrete mixes in a dataset."""
        logger.info(f"Validating mixes for dataset {dataset.dataset_name}")
        stats = {
            'mixes_count': 0,
            'mixes_issues': [],
            'mixes_warnings': [],
            'w_c_ratio_stats': {},
            'w_b_ratio_stats': {}
        }
        
        try:
            # Count mixes
            mixes = ConcreteMix.objects.filter(dataset=dataset)
            mix_count = mixes.count()
            stats['mixes_count'] = mix_count
            
            if mix_count == 0:
                stats['mixes_issues'].append(f"No mixes found in dataset {dataset.dataset_name}")
                return stats
            
            logger.info(f"Found {mix_count} mixes in dataset {dataset.dataset_name}")
            self.stats['mixes_validated'] += mix_count
            
            # Check water-cement ratios
            w_c_ratio_stats = self.validate_mix_ratios(mixes, 'w_c_ratio')
            stats['w_c_ratio_stats'] = w_c_ratio_stats
            
            # Check water-binder ratios
            w_b_ratio_stats = self.validate_mix_ratios(mixes, 'w_b_ratio')
            stats['w_b_ratio_stats'] = w_b_ratio_stats
            
            return stats
        
        except Exception as e:
            error_msg = f"Error validating mixes: {str(e)}"
            logger.error(error_msg)
            stats['mixes_issues'].append(error_msg)
            return stats
    
    def validate_mix_ratios(self, mixes_queryset, ratio_field: str) -> Dict[str, Any]:
        """Validate water-cement or water-binder ratios."""
        stats = {
            'min': None,
            'max': None,
            'avg': None,
            'mixes_with_invalid_ratios': [],
            'mixes_with_missing_ratios': []  
        }
        
        try:
            # Get threshold values
            threshold = self.thresholds.get(ratio_field, {'min': 0.2, 'max': 0.9})
            
            # Find mixes with missing ratio values
            missing_filter = {f"{ratio_field}__isnull": True}
            mixes_missing_ratio = mixes_queryset.filter(**missing_filter).values_list('mix_code', flat=True)
            stats['mixes_with_missing_ratios'] = list(mixes_missing_ratio)
            
            if len(mixes_missing_ratio) > 0:
                logger.warning(f"Found {len(mixes_missing_ratio)} mixes with missing {ratio_field}")
                self.stats['validation_warnings'].append(
                    f"{len(mixes_missing_ratio)} mixes have missing {ratio_field}: {list(mixes_missing_ratio)}"
                )
            
            # Find mixes with invalid ratio values
            low_filter = {f"{ratio_field}__lt": threshold['min'], f"{ratio_field}__isnull": False}
            high_filter = {f"{ratio_field}__gt": threshold['max'], f"{ratio_field}__isnull": False}
            
            mixes_with_low_ratios = mixes_queryset.filter(**low_filter).values_list('mix_code', ratio_field)
            mixes_with_high_ratios = mixes_queryset.filter(**high_filter).values_list('mix_code', ratio_field)
            
            # Combine invalid mixes
            invalid_mixes = []
            for mix_code, ratio in mixes_with_low_ratios:
                invalid_mixes.append({
                    'mix_code': mix_code, 
                    'ratio': ratio, 
                    'issue': f"{ratio_field} too low"
                })
                
            for mix_code, ratio in mixes_with_high_ratios:
                invalid_mixes.append({
                    'mix_code': mix_code, 
                    'ratio': ratio, 
                    'issue': f"{ratio_field} too high"
                })
                
            stats['mixes_with_invalid_ratios'] = invalid_mixes
            
            if len(invalid_mixes) > 0:
                logger.warning(f"Found {len(invalid_mixes)} mixes with invalid {ratio_field}")
                self.stats['validation_errors'].append(
                    f"{len(invalid_mixes)} mixes have invalid {ratio_field}"
                )
            
            # Calculate statistics for valid ratios
            valid_mixes = mixes_queryset.exclude(**missing_filter).exclude(**low_filter).exclude(**high_filter)
            if valid_mixes.exists():
                agg_results = valid_mixes.aggregate(
                    min_ratio=Min(ratio_field),
                    max_ratio=Max(ratio_field),
                    avg_ratio=Avg(ratio_field)
                )
                
                stats['min'] = agg_results['min_ratio']
                stats['max'] = agg_results['max_ratio']
                stats['avg'] = agg_results['avg_ratio']
                
                logger.info(f"{ratio_field} stats - Min: {stats['min']:.2f}, Max: {stats['max']:.2f}, Avg: {stats['avg']:.2f}")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error validating {ratio_field}: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'mixes_with_missing_ratios': [],
                'mixes_with_invalid_ratios': []
            }
            
    def validate_components(self, dataset: Dataset) -> Dict[str, Any]:
        """Validate concrete mix components in a dataset."""
        logger.info(f"Validating components for dataset {dataset.dataset_name}")
        stats = {
            'components_count': 0,
            'components_by_type': {},
            'components_issues': [],
            'components_warnings': []
        }
        
        try:
            # Get all mixes in the dataset
            mixes = ConcreteMix.objects.filter(dataset=dataset)
            
            if not mixes.exists():
                stats['components_warnings'].append(f"No mixes found in dataset {dataset.dataset_name}")
                return stats
            
            # Get all components for these mixes
            components = MixComponent.objects.filter(mix__dataset=dataset)
            component_count = components.count()
            stats['components_count'] = component_count
            
            if component_count == 0:
                stats['components_issues'].append(f"No components found for any mixes in dataset {dataset.dataset_name}")
                return stats
            
            logger.info(f"Found {component_count} components in dataset {dataset.dataset_name}")
            self.stats['components_validated'] += component_count
            
            # Check for essential component types (cement, water, aggregates)
            essential_components = {
                'cement': 'CEMENT',
                'water': 'WATER',
                'aggregate': ['FINE_AGGREGATE', 'COARSE_AGGREGATE']
            }
            
            # Count components by type
            component_counts = {}
            mixes_with_components = {}
            
            for material_name, class_code in essential_components.items():
                if isinstance(class_code, list):
                    # For aggregate, we need to look for either fine or coarse
                    component_counts[material_name] = 0
                    for code in class_code:
                        count = components.filter(material__material_class__name__icontains=code.lower().replace('_', ' ')).count()
                        component_counts[material_name] += count
                else:
                    # For cement and water, direct match
                    try:
                        # Using direct string comparison instead of icontains
                        component_counts[material_name] = components.filter(
                            material__material_class__name__iexact=class_code.lower()
                        ).count()
                    except Exception as e:
                        logger.warning(f"Error querying {material_name} components: {str(e)}")
                        # Try alternative approach using the name field directly
                        try:
                            component_counts[material_name] = components.filter(
                                material__name__icontains=material_name
                            ).count()
                        except Exception as e2:
                            logger.error(f"Failed alternative query for {material_name}: {str(e2)}")
                            component_counts[material_name] = 0
                    
                # Check if each mix has this component
                mixes_with_this_component = set()
                try:
                    # Get the mix field's related model and its primary key field name
                    mix_field = MixComponent._meta.get_field('mix')
                    mix_model = mix_field.related_model
                    mix_pk_field = mix_model._meta.pk.name
                    logger.debug(f"Mix model primary key field: {mix_pk_field}")
                    
                    # Now use this field name for the lookup
                    mix_id_field = 'mix__' + mix_pk_field
                    
                    if isinstance(class_code, list):
                        for code in class_code:
                            try:
                                # Try with exact match first
                                mix_ids = components.filter(
                                    material__name__icontains=code.lower().replace('_', ' ')
                                ).values_list(mix_id_field, flat=True)
                            except Exception:
                                # Fall back to material name
                                mix_ids = components.filter(
                                    material__name__icontains=code.split('_')[-1].lower()
                                ).values_list(mix_id_field, flat=True)
                            mixes_with_this_component.update(mix_ids)
                    else:
                        try:
                            # Try with exact match first
                            mix_ids = components.filter(
                                material__name__icontains=material_name
                            ).values_list(mix_id_field, flat=True)
                        except Exception:
                            # Fall back to simpler query
                            mix_ids = components.filter(
                                material__name__icontains=material_name
                            ).values_list(mix_id_field, flat=True)
                        mixes_with_this_component.update(mix_ids)
                except Exception as e:
                    logger.error(f"Error getting mix components: {str(e)}")
                    mix_ids = []
                    mixes_with_this_component.update(mix_ids)
                
                mixes_with_components[material_name] = len(mixes_with_this_component)
                
                # Check for mixes missing this component type
                # Get the primary key field for the ConcreteMix model
                mix_pk_field = ConcreteMix._meta.pk.name
                try:
                    # Use the correct primary key field name in the filter
                    filter_kwargs = {f"{mix_pk_field}__in": mixes_with_this_component}
                    mixes_missing_component = mixes.exclude(**filter_kwargs)
                    
                    if mixes_missing_component.exists():
                        missing_mix_codes = list(mixes_missing_component.values_list('mix_code', flat=True))
                        warning = f"{len(missing_mix_codes)} mixes missing {material_name}: {missing_mix_codes}"
                        stats['components_warnings'].append(warning)
                        logger.warning(warning)
                except Exception as e:
                    logger.error(f"Error checking for mixes missing {material_name}: {str(e)}")
                    stats['components_warnings'].append(f"Could not validate mixes for {material_name} components: {str(e)}")

            
            stats['components_by_type'] = component_counts
            stats['mixes_with_components'] = mixes_with_components
            
            # Validate cement-to-binder ratios
            if component_counts.get('cement', 0) > 0:
                # Calculate supplementary materials (fly ash, silica fume, etc)
                supplementary = components.filter(
                    material__material_class__name__in=['FLY_ASH', 'SILICA_FUME', 'SLAG', 'METAKAOLIN']
                ).count()
                
                stats['supplementary_materials'] = supplementary
                
                if supplementary > 0:
                    logger.info(f"Found {supplementary} supplementary cementitious material components")
                    # We should verify that w/b ratio < w/c ratio for mixes with SCMs
                    mixes_with_scm = ConcreteMix.objects.filter(
                        dataset=dataset,
                        components__material__material_class__name__in=['FLY_ASH', 'SILICA_FUME', 'SLAG', 'METAKAOLIN']
                    ).distinct()
                    
                    # Check w/b vs w/c ratios
                    for mix in mixes_with_scm:
                        if mix.w_c_ratio is not None and mix.w_b_ratio is not None:
                            if mix.w_b_ratio >= mix.w_c_ratio:
                                warning = f"Mix {mix.mix_code} has w/b ratio ({mix.w_b_ratio:.2f}) ≥ w/c ratio ({mix.w_c_ratio:.2f}), which is suspicious"
                                stats['components_warnings'].append(warning)
                                logger.warning(warning)
            
            return stats
            
        except Exception as e:
            error_msg = f"Error validating components: {str(e)}"
            logger.error(error_msg)
            stats['components_issues'].append(error_msg)
            return stats
    
    def validate_performance_results(self, dataset: Dataset) -> Dict[str, Any]:
        """Validate performance results for a dataset."""
        logger.info(f"Validating performance results for dataset {dataset.dataset_name}")
        stats = {
            'results_count': 0,
            'results_by_category': {},
            'results_issues': [],
            'results_warnings': []
        }
        
        try:
            # Get all mixes in the dataset
            mixes = ConcreteMix.objects.filter(dataset=dataset)
            
            if not mixes.exists():
                stats['results_warnings'].append(f"No mixes found in dataset {dataset.dataset_name}")
                return stats
            
            # Get all performance results for these mixes
            results = PerformanceResult.objects.filter(mix__dataset=dataset)
            results_count = results.count()
            stats['results_count'] = results_count
            
            if results_count == 0:
                stats['results_issues'].append(f"No performance results found for any mixes in dataset {dataset.dataset_name}")
                return stats
            
            logger.info(f"Found {results_count} performance results in dataset {dataset.dataset_name}")
            self.stats['results_validated'] += results_count
            
            # Analyze performance results by category
            # Handle custom primary key naming (lesson learned)
            try:
                # Get primary key field for PerformanceResult model
                perf_pk_field = PerformanceResult._meta.pk.name
                logger.debug(f"PerformanceResult primary key field: {perf_pk_field}")
                
                # Use the correct primary key field in the aggregation
                categories = results.values('category').annotate(count=Count(perf_pk_field))
                stats['results_by_category'] = {cat['category']: cat['count'] for cat in categories}
                
                logger.info(f"Performance results by category: {stats['results_by_category']}")
                
                # Check for mixes without performance results
                # Get mix primary key field
                mix_field = PerformanceResult._meta.get_field('mix')
                mix_model = mix_field.related_model
                mix_pk_field = mix_model._meta.pk.name
                logger.debug(f"Mix model primary key field via PerformanceResult: {mix_pk_field}")
                
                # Construct the field name for query
                mix_id_field = f"mix__{mix_pk_field}"
                
                # Get mixes with results
                mixes_with_results = set(results.values_list('mix__mix_id', flat=True))
                
                # Exclude these mixes to find those without results
                filter_kwargs = {f"{mix_pk_field}__in": mixes_with_results}
                mixes_without_results = mixes.exclude(**filter_kwargs)
                
                if mixes_without_results.exists():
                    missing_mix_codes = list(mixes_without_results.values_list('mix_code', flat=True))
                    warning = f"{len(missing_mix_codes)} mixes have no performance results: {missing_mix_codes}"
                    stats['results_warnings'].append(warning)
                    logger.warning(warning)
            except Exception as e:
                logger.error(f"Error analyzing performance results by category: {str(e)}")
                stats['results_warnings'].append(f"Could not fully analyze performance results: {str(e)}")

            
            # Validate compressive strength values
            self.validate_property_values(results, dataset, stats)
            
            return stats
            
        except Exception as e:
            error_msg = f"Error validating performance results: {str(e)}"
            logger.error(error_msg)
            stats['results_issues'].append(error_msg)
            return stats
    
    def validate_property_values(self, results_queryset, dataset: Dataset, stats: Dict[str, Any]):
        """Validate specific property values for reasonableness."""
        # Check compressive strength values
        try:
            # Using more robust filter conditions that don't rely on specific field names
            # Get compressive strength results
            try:
                # First try with test_method description
                strength_results = results_queryset.filter(
                    Q(test_method__description__icontains='compressive')
                )
                if not strength_results.exists():
                    # Fall back to category
                    strength_results = results_queryset.filter(
                        Q(category='hardened')
                    )
            except Exception as e:
                logger.warning(f"Error with test_method lookup: {str(e)}")
                # Last resort - try to find results with value_num above certain threshold
                strength_results = results_queryset.filter(
                    Q(value_num__gt=5.0)
                )
            
            if strength_results.exists():
                logger.info(f"Found {strength_results.count()} compressive strength results to validate")
                
                # Look for suspiciously low or high values
                threshold = self.thresholds.get('compressive_strength', {'min': 5.0, 'max': 120.0})
                
                low_strength = strength_results.filter(value_num__lt=threshold['min'])
                high_strength = strength_results.filter(value_num__gt=threshold['max'])
                
                if low_strength.exists():
                    low_values = [f"{r.mix.mix_code}: {r.value_num} MPa" for r in low_strength]
                    warning = f"Found {low_strength.count()} suspiciously low strength values: {low_values}"
                    stats['results_warnings'].append(warning)
                    logger.warning(warning)
                
                if high_strength.exists():
                    high_values = [f"{r.mix.mix_code}: {r.value_num} MPa" for r in high_strength]
                    warning = f"Found {high_strength.count()} suspiciously high strength values: {high_values}"
                    stats['results_warnings'].append(warning)
                    logger.warning(warning)
                
                # Get statistics for valid strength values
                valid_strength = strength_results.exclude(
                    Q(value_num__lt=threshold['min']) | Q(value_num__gt=threshold['max'])
                )
                
                if valid_strength.exists():
                    agg_results = valid_strength.aggregate(
                        min_val=Min('value_num'),
                        max_val=Max('value_num'),
                        avg_val=Avg('value_num')
                    )
                    
                    stats['strength_stats'] = {
                        'min': agg_results['min_val'],
                        'max': agg_results['max_val'],
                        'avg': agg_results['avg_val']
                    }
                    
                    logger.info(f"Strength stats - Min: {agg_results['min_val']:.1f} MPa, "
                               f"Max: {agg_results['max_val']:.1f} MPa, "
                               f"Avg: {agg_results['avg_val']:.1f} MPa")
        
        except Exception as e:
            logger.error(f"Error validating property values: {str(e)}")
            stats['results_issues'].append(f"Error validating property values: {str(e)}")
    
    def run(self):
        """Run the validation sequence."""
        logger.info("Starting Validation Run")
        self.update_status("Start", "Starting Validation Run")
        
        # Validate all datasets (or specified target datasets)
        validation_results = self.validate_datasets()
        
        # Generate validation report
        report_path = self.generate_validation_report(validation_results)
        
        # Complete the validation run
        duration = datetime.datetime.now() - self.start_time
        issues_count = len(self.stats['validation_errors'])
        warnings_count = len(self.stats['validation_warnings'])
        
        completion_message = (
            f"Validation Run completed in {duration.total_seconds():.1f} seconds. "
            f"Found {issues_count} issues and {warnings_count} warnings."
        )
        logger.info(completion_message)
        self.update_status("Complete", completion_message, issues_count > 0)
        
        return {
            'stats': self.stats,
            'validation_results': validation_results,
            'report_path': report_path,
            'duration': duration.total_seconds()
        }
    
    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """Generate a detailed validation report and save it to disk.
        
        Args:
            validation_results: The validation results to include in the report
            
        Returns:
            Path to the generated report file
        """
        report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validation_report.json')
        
        try:
            # Add timestamp and summary info to the report
            report_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'summary': {
                    'datasets_validated': self.stats['datasets_validated'],
                    'mixes_validated': self.stats['mixes_validated'],
                    'components_validated': self.stats['components_validated'],
                    'results_validated': self.stats['results_validated'],
                    'errors_count': len(self.stats['validation_errors']),
                    'warnings_count': len(self.stats['validation_warnings'])
                },
                'errors': self.stats['validation_errors'],
                'warnings': self.stats['validation_warnings'],
                'validation_results': validation_results
            }
            
            # Write the report to disk
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            logger.info(f"Validation report saved to {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"Failed to generate validation report: {str(e)}")
            return ""


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Validation Run for Phase 3 of Database Refresh Plan')
    parser.add_argument('--datasets', '-d', type=str, nargs='+', 
                        help='List of dataset codes to validate (e.g., TEST_DS PERF_TEST)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                        help='Enable verbose output')
    parser.add_argument('--report', '-r', type=str,
                        help='Custom location for the validation report')
    
    args = parser.parse_args()
    
    # Set up more detailed logging if verbose mode is enabled
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        # Add a more verbose file handler
        verbose_handler = logging.FileHandler('validation_run_verbose.log')
        verbose_handler.setLevel(logging.DEBUG)
        verbose_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(verbose_handler)
        
        print("Verbose logging enabled - check validation_run_verbose.log for detailed logs")
    
    print("====================================================================")
    print("Starting Validation Run for Phase 3: Test Migration")
    print("====================================================================")
    print(f"Starting at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.datasets:
        print(f"Validating specific datasets: {', '.join(args.datasets)}")
    else:
        print("Validating all available datasets")
        
    # Create and run the validation
    validation_run = ValidationRun(target_datasets=args.datasets)
    results = validation_run.run()
    
    print("\n====================================================================")
    print("Validation Run Complete")
    print("====================================================================")
    
    # Print a summary of the validation results
    print("\nValidation Summary:")
    print("-----------------")
    print(f"Datasets validated: {results['stats']['datasets_validated']}")
    print(f"Mixes validated: {results['stats']['mixes_validated']}")
    print(f"Components validated: {results['stats']['components_validated']}")
    print(f"Results validated: {results['stats']['results_validated']}")
    print(f"Issues found: {len(results['stats']['validation_errors'])}")
    print(f"Warnings found: {len(results['stats']['validation_warnings'])}")
    
    # Print errors and warnings
    if results['stats']['validation_errors']:
        print("\nErrors:")
        print("-------")
        for idx, error in enumerate(results['stats']['validation_errors'], 1):
            print(f"{idx}. {error}")
    
    if results['stats']['validation_warnings']:
        print("\nWarnings:")
        print("---------")
        for idx, warning in enumerate(results['stats']['validation_warnings'], 1):
            print(f"{idx}. {warning}")
    
    print(f"\nDetailed validation report saved to: {results['report_path']}")
    print(f"\nTotal runtime: {results['duration']:.2f} seconds")
    
    # Final message
    if len(results['stats']['validation_errors']) == 0:
        print("\nValidation completed successfully! No critical issues found.")
        print("You can proceed to the Performance Testing phase of the Database Refresh Plan.")
    else:
        print("\nValidation completed with errors. Please fix the issues before proceeding.")
        print("Review the detailed validation report for more information.")
    
    print("\n====================================================================")
