#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Dataset Validation Script

This script performs comprehensive validation checks on all 6 concrete mix datasets
to ensure they've been imported correctly and identify any potential issues.
'''

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from datetime import datetime
import pickle
from collections import defaultdict

# Django setup for database access
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
import django
django.setup()

# Import Django models using the same pattern as concrete_data_analysis.py
from django.db.models import Count, Q, F, Sum, Avg, Case, When, Value, FloatField
from cdb_app import models as cdb

# Configure logging
log_dir = 'validation_logs'
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f'validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = 'validation_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def log_section(section_title):
    """Helper to log section headers consistently."""
    logger.info(f'\n{"=" * 20} {section_title} {"=" * 20}\n')


def fetch_dataset_metadata():
    """Fetch metadata about all datasets in the database."""
    datasets = cdb.Dataset.objects.using('cdb').all()
    metadata = []
    
    for ds in datasets:
        mix_count = cdb.ConcreteMix.objects.using('cdb').filter(dataset=ds).count()
        metadata.append({
            'id': ds.dataset_id,
            'name': ds.dataset_name,
            'description': getattr(ds, 'description', None),
            'mix_count': mix_count
        })
    
    return pd.DataFrame(metadata)


def fetch_all_mixes():
    """Fetch all concrete mixes with their components."""
    log_section("Fetching All Mixes")
    
    # Fetch all mixes - match query format used in concrete_data_analysis.py
    mixes = list(cdb.ConcreteMix.objects.using('cdb')
                .select_related('dataset')
                .all())
    
    logger.info(f"Fetched {len(mixes)} total mixes")
    
    # Create a list to hold all mix data
    mix_data = []
    
    # Track components for each mix
    component_counts = defaultdict(int)
    material_type_issues = []
    
    # Process each mix
    for mix in mixes:
        # Basic mix data
        mix_dict = {
            'mix_id': mix.mix_id,
            'dataset_id': mix.dataset.dataset_id,
            'dataset_name': mix.dataset.dataset_name,
            'water_kg_m3': getattr(mix, 'water_kg_m3', None),
            'slump_mm': getattr(mix, 'slump_mm', None),
            'w_c_ratio': mix.w_c_ratio,
            'w_b_ratio': mix.w_b_ratio,
        }
        
        # Component data
        cement_kg = 0
        scm_kg = 0
        has_cement = False
        has_scm = False
        coarse_agg_kg = 0
        fine_agg_kg = 0
        mix_components = defaultdict(list)
        
        # Track component counts for statistical analysis
        mix_component_count = 0
        
        # Fetch components using MixComponent model (similar to concrete_data_analysis.py)
        components = cdb.MixComponent.objects.using('cdb').filter(mix=mix).select_related('material')
        
        for comp in components:
            mix_component_count += 1
            material_class = comp.material.material_class_id if comp.material else None
            dosage = comp.dosage_kg_m3 or 0
            
            # Check for unusual material classes
            if material_class not in ['CEMENT', 'SCM', 'AGGR_C', 'AGGR_F', 'WATER', 'ADMIX', 'OTHER', None]:
                material_type_issues.append({
                    'mix_id': mix.mix_id,
                    'dataset_name': mix.dataset.dataset_name,
                    'material_class': material_class,
                    'subtype': comp.material.subtype_code if comp.material else None
                })
            
            # Store component details
            mix_components[material_class].append({
                'subtype': comp.material.subtype_code if comp.material else None,
                'dosage_kg_m3': dosage
            })
            
            # Track material type quantities
            if material_class == 'CEMENT':
                cement_kg += dosage
                has_cement = True
                mix_dict['cement_type'] = comp.material.subtype_code if comp.material else None
            elif material_class == 'SCM':
                scm_kg += dosage
                has_scm = True
                mix_dict['scm_primary_raw'] = comp.material.subtype_code if comp.material else None
                mix_dict['scm_quantity_kg_m3'] = dosage
            elif material_class == 'AGGR_C':
                coarse_agg_kg += dosage
            elif material_class == 'AGGR_F':
                fine_agg_kg += dosage
        
        # Record component count
        component_counts[mix_component_count] += 1
        
        # Add component summaries
        mix_dict['cement_kg_m3'] = cement_kg
        mix_dict['total_scm_kg_m3'] = scm_kg
        mix_dict['has_cement'] = has_cement
        mix_dict['has_scm'] = has_scm
        mix_dict['coarse_agg_kg_m3'] = coarse_agg_kg
        mix_dict['fine_agg_kg_m3'] = fine_agg_kg
        mix_dict['component_count'] = mix_component_count
        
        # Verify if we have basic components for a valid concrete mix
        mix_dict['has_basic_components'] = has_cement and (mix_dict['water_kg_m3'] is not None)
        
        # Strength results - access directly from mix attributes
        strength_data = []
        
        # Check for common strength test day values
        strength_days = [1, 3, 7, 14, 28, 56, 90, 180, 360]
        for days in strength_days:
            # Try various attribute naming patterns for compressive strength
            strength_value = None
            
            # Pattern 1: compressive_strength_28d_mpa
            attr_name = f'compressive_strength_{days}d_mpa'
            if hasattr(mix, attr_name):
                strength_value = getattr(mix, attr_name)
            
            # Pattern 2: strength_28d
            if strength_value is None:
                attr_name = f'strength_{days}d'
                if hasattr(mix, attr_name):
                    strength_value = getattr(mix, attr_name)
            
            # If we found a strength value, add it to the mix dict
            if strength_value is not None:
                days_key = f'compressive_strength_{days}d_mpa'
                mix_dict[days_key] = strength_value
                strength_data.append({
                    'age_days': days,
                    'compressive_strength_mpa': strength_value
                })
        
        mix_dict['has_strength_data'] = len(strength_data) > 0
        mix_dict['strength_test_count'] = len(strength_data)
        
        mix_data.append(mix_dict)
    
    # Convert to DataFrame
    df = pd.DataFrame(mix_data)
    logger.info(f"Created initial dataframe with {len(df)} rows")
    
    # Log component distribution
    logger.info("Component count distribution:")
    for count, num_mixes in sorted(component_counts.items()):
        logger.info(f"  {count} components: {num_mixes} mixes ({num_mixes/len(df)*100:.1f}%)")
    
    # Log unusual material types
    if material_type_issues:
        logger.warning(f"Found {len(material_type_issues)} components with unusual material types")
        material_issues_df = pd.DataFrame(material_type_issues)
        material_issues_path = os.path.join(OUTPUT_DIR, 'unusual_material_types.csv')
        material_issues_df.to_csv(material_issues_path, index=False)
        logger.info(f"Saved unusual material types to {material_issues_path}")
    
    return df


def validate_dataset_completeness(df):
    """Check for completeness issues in each dataset."""
    log_section("Dataset Completeness Analysis")
    
    # Group by dataset
    datasets = df['dataset_name'].unique()
    logger.info(f"Found {len(datasets)} datasets: {', '.join(datasets)}")
    
    # Initialize results table
    results = []
    
    for dataset in datasets:
        # Filter to this dataset
        ds_df = df[df['dataset_name'] == dataset]
        
        # Basic counts
        total_mixes = len(ds_df)
        mixes_with_cement = ds_df['has_cement'].sum()
        mixes_with_scm = ds_df['has_scm'].sum()
        mixes_with_w_c = ds_df['w_c_ratio'].notna().sum()
        mixes_with_w_b = ds_df['w_b_ratio'].notna().sum()
        mixes_with_28d = ds_df['compressive_strength_28d_mpa'].notna().sum() if 'compressive_strength_28d_mpa' in ds_df else 0
        mixes_with_basic = ds_df['has_basic_components'].sum()
        
        # Get columns with strength data
        strength_cols = [col for col in ds_df.columns if col.startswith('compressive_strength_') and col.endswith('_mpa')]
        strength_days = [int(col.split('_')[2].replace('d', '')) for col in strength_cols]
        
        # Check which strength days are available
        strength_days_coverage = {}
        for col in strength_cols:
            days = col.split('_')[2].replace('d', '')
            coverage = ds_df[col].notna().sum() / total_mixes * 100 if total_mixes > 0 else 0
            strength_days_coverage[days] = coverage
        
        # Calculate percentages
        pct_with_cement = mixes_with_cement / total_mixes * 100 if total_mixes > 0 else 0
        pct_with_scm = mixes_with_scm / total_mixes * 100 if total_mixes > 0 else 0
        pct_with_w_c = mixes_with_w_c / total_mixes * 100 if total_mixes > 0 else 0
        pct_with_w_b = mixes_with_w_b / total_mixes * 100 if total_mixes > 0 else 0
        pct_with_28d = mixes_with_28d / total_mixes * 100 if total_mixes > 0 else 0
        pct_with_basic = mixes_with_basic / total_mixes * 100 if total_mixes > 0 else 0
        
        # Add to results
        results.append({
            'dataset': dataset,
            'total_mixes': total_mixes,
            'mixes_with_cement': mixes_with_cement,
            'mixes_with_scm': mixes_with_scm,
            'mixes_with_w_c': mixes_with_w_c,
            'mixes_with_w_b': mixes_with_w_b,
            'mixes_with_28d': mixes_with_28d,
            'mixes_with_basic': mixes_with_basic,
            'pct_with_cement': pct_with_cement,
            'pct_with_scm': pct_with_scm,
            'pct_with_w_c': pct_with_w_c,
            'pct_with_w_b': pct_with_w_b,
            'pct_with_28d': pct_with_28d,
            'pct_with_basic': pct_with_basic,
            'strength_days': sorted(strength_days),
            'strength_days_coverage': strength_days_coverage
        })
        
        # Log detailed dataset info
        logger.info(f"Dataset: {dataset}")
        logger.info(f"  Total mixes: {total_mixes}")
        logger.info(f"  Mixes with cement: {mixes_with_cement} ({pct_with_cement:.1f}%)")
        logger.info(f"  Mixes with SCM: {mixes_with_scm} ({pct_with_scm:.1f}%)")
        logger.info(f"  Mixes with w/c ratio: {mixes_with_w_c} ({pct_with_w_c:.1f}%)")
        logger.info(f"  Mixes with w/b ratio: {mixes_with_w_b} ({pct_with_w_b:.1f}%)")
        logger.info(f"  Mixes with 28-day strength: {mixes_with_28d} ({pct_with_28d:.1f}%)")
        logger.info(f"  Mixes with basic components: {mixes_with_basic} ({pct_with_basic:.1f}%)")
        logger.info(f"  Strength test days: {sorted(strength_days)}")
        
    # Save results to CSV
    results_df = pd.DataFrame(results)
    output_path = os.path.join(OUTPUT_DIR, 'dataset_completeness.csv')
    results_df.to_csv(output_path, index=False)
    logger.info(f"Saved dataset completeness analysis to {output_path}")
    
    return results_df


def validate_data_consistency(df):
    """Check for internal consistency and validate ratio calculations."""
    log_section("Data Consistency Validation")
    
    # Initialize counters for inconsistency types
    inconsistency_counts = defaultdict(int)
    inconsistency_examples = defaultdict(list)
    
    # Check for w/c ratio inconsistencies
    logger.info("Checking w/c ratio consistency...")
    wc_df = df[(df['water_kg_m3'].notna()) & (df['cement_kg_m3'] > 0) & (df['w_c_ratio'].notna())].copy()
    
    if len(wc_df) > 0:
        # Calculate w/c ratio from raw values
        wc_df['calc_w_c_ratio'] = wc_df['water_kg_m3'] / wc_df['cement_kg_m3']
        
        # Check for significant discrepancies
        wc_df['w_c_diff'] = abs(wc_df['w_c_ratio'] - wc_df['calc_w_c_ratio'])
        wc_df['w_c_diff_pct'] = wc_df['w_c_diff'] / wc_df['w_c_ratio'] * 100
        
        # Flag significant discrepancies (>5% difference)
        wc_issues = wc_df[wc_df['w_c_diff_pct'] > 5].copy()
        inconsistency_counts['w_c_ratio'] = len(wc_issues)
        
        if len(wc_issues) > 0:
            logger.warning(f"Found {len(wc_issues)} mixes with w/c ratio inconsistencies (>5% difference)")
            inconsistency_examples['w_c_ratio'] = wc_issues.head(5)[['mix_id', 'dataset_name', 'w_c_ratio', 'calc_w_c_ratio', 'w_c_diff_pct']].to_dict('records')
            # Save detailed issues
            wc_issues_path = os.path.join(OUTPUT_DIR, 'wc_ratio_inconsistencies.csv')
            wc_issues.to_csv(wc_issues_path, index=False)
            logger.info(f"Saved w/c ratio inconsistencies to {wc_issues_path}")
        else:
            logger.info("No significant w/c ratio inconsistencies found")
    
    # Check for total mix proportions consistency
    logger.info("Checking mix proportions consistency...")
    
    # Filter to mixes with all basic components
    mix_props_df = df[(df['cement_kg_m3'].notna()) & 
                      (df['water_kg_m3'].notna()) & 
                      (df['coarse_agg_kg_m3'].notna()) & 
                      (df['fine_agg_kg_m3'].notna())].copy()
    
    if len(mix_props_df) > 0:
        # Calculate total weight and check for reasonable density
        # Typical concrete density is between 2200-2600 kg/m³
        mix_props_df['total_weight'] = (mix_props_df['cement_kg_m3'] + 
                                      mix_props_df['total_scm_kg_m3'] + 
                                      mix_props_df['water_kg_m3'] + 
                                      mix_props_df['coarse_agg_kg_m3'] + 
                                      mix_props_df['fine_agg_kg_m3'])
        
        # Flag mixes with very low or high density
        density_issues = mix_props_df[(mix_props_df['total_weight'] < 2000) | 
                                  (mix_props_df['total_weight'] > 2800)].copy()
        
        inconsistency_counts['density'] = len(density_issues)
        
        if len(density_issues) > 0:
            logger.warning(f"Found {len(density_issues)} mixes with unusual density (<2000 or >2800 kg/m³)")
            inconsistency_examples['density'] = density_issues.head(5)[['mix_id', 'dataset_name', 'total_weight']].to_dict('records')
            # Save detailed issues
            density_issues_path = os.path.join(OUTPUT_DIR, 'unusual_density_mixes.csv')
            density_issues.to_csv(density_issues_path, index=False)
            logger.info(f"Saved unusual density mixes to {density_issues_path}")
        else:
            logger.info("No significant density inconsistencies found")
    
    # Check for unrealistic strength values
    logger.info("Checking for unrealistic strength values...")
    
    strength_cols = [col for col in df.columns if col.startswith('compressive_strength_') and col.endswith('_mpa')]
    strength_issues_all = []
    
    for col in strength_cols:
        # Flag extremely low or high strengths
        strength_issues = df[(df[col] < 1) | (df[col] > 150)].copy()
        
        if len(strength_issues) > 0:
            age_days = col.split('_')[2].replace('d', '')
            logger.warning(f"Found {len(strength_issues)} mixes with unrealistic {age_days}-day strength values (<1 or >150 MPa)")
            strength_issues['strength_col'] = col
            strength_issues['strength_value'] = strength_issues[col]
            strength_issues_all.append(strength_issues[['mix_id', 'dataset_name', 'strength_col', 'strength_value']])
            inconsistency_counts[f'strength_{age_days}d'] = len(strength_issues)
    
    if strength_issues_all:
        strength_issues_df = pd.concat(strength_issues_all)
        inconsistency_examples['strength'] = strength_issues_df.head(5).to_dict('records')
        # Save detailed issues
        strength_issues_path = os.path.join(OUTPUT_DIR, 'unrealistic_strength_values.csv')
        strength_issues_df.to_csv(strength_issues_path, index=False)
        logger.info(f"Saved unrealistic strength values to {strength_issues_path}")
    else:
        logger.info("No unrealistic strength values found")
    
    # Summarize all inconsistencies
    logger.info("Summary of data consistency issues:")
    for issue_type, count in inconsistency_counts.items():
        logger.info(f"  {issue_type}: {count} issues")
    
    # Save examples of inconsistencies to JSON
    if inconsistency_examples:
        import json
        examples_path = os.path.join(OUTPUT_DIR, 'inconsistency_examples.json')
        with open(examples_path, 'w') as f:
            json.dump(inconsistency_examples, f, indent=2)
        logger.info(f"Saved inconsistency examples to {examples_path}")
    
    return inconsistency_counts


def analyze_dataset_scm_types(df):
    """Analyze SCM types and proportions across datasets."""
    log_section("SCM Types Analysis")
    
    # Get all datasets
    datasets = df['dataset_name'].unique()
    
    # Prepare for collecting results
    results = []
    
    # Analyze each dataset
    for dataset in datasets:
        # Filter to this dataset
        ds_df = df[df['dataset_name'] == dataset]
        
        # Count SCM types
        scm_counts = ds_df['scm_primary_raw'].value_counts()
        total_mixes = len(ds_df)
        scm_mixes = ds_df['has_scm'].sum()
        scm_pct = scm_mixes / total_mixes * 100 if total_mixes > 0 else 0
        
        # Log SCM types in this dataset
        logger.info(f"Dataset: {dataset}")
        logger.info(f"  Total mixes: {total_mixes}")
        logger.info(f"  Mixes with SCM: {scm_mixes} ({scm_pct:.1f}%)")
        
        if scm_mixes > 0:
            # Log top SCM types
            logger.info("  Top SCM types:")
            for scm_type, count in scm_counts.head(5).items():
                if pd.notna(scm_type):
                    pct = count / scm_mixes * 100
                    logger.info(f"    {scm_type}: {count} ({pct:.1f}%)")
            
            # Analyze SCM replacement percentages
            if 'scm_replacement_pct' in ds_df.columns:
                valid_scm_pct = ds_df[ds_df['scm_replacement_pct'].notna()]
                if len(valid_scm_pct) > 0:
                    mean_replacement = valid_scm_pct['scm_replacement_pct'].mean()
                    median_replacement = valid_scm_pct['scm_replacement_pct'].median()
                    min_replacement = valid_scm_pct['scm_replacement_pct'].min()
                    max_replacement = valid_scm_pct['scm_replacement_pct'].max()
                    
                    logger.info(f"  SCM replacement %: mean={mean_replacement:.1f}, median={median_replacement:.1f}, range={min_replacement:.1f}-{max_replacement:.1f}")
        
        # Save SCM details for this dataset
        if scm_mixes > 0:
            # Create detailed SCM analysis for this dataset
            scm_types = {}
            for scm_type, count in scm_counts.items():
                if pd.notna(scm_type):
                    scm_types[scm_type] = {
                        'count': int(count),
                        'percentage': float(count / scm_mixes * 100)
                    }
            
            result = {
                'dataset': dataset,
                'total_mixes': total_mixes,
                'scm_mixes': scm_mixes,
                'scm_percentage': scm_pct,
                'scm_types': scm_types
            }
            
            # Add SCM replacement stats if available
            if 'scm_replacement_pct' in ds_df.columns:
                valid_scm_pct = ds_df[ds_df['scm_replacement_pct'].notna()]
                if len(valid_scm_pct) > 0:
                    result['mean_replacement'] = float(valid_scm_pct['scm_replacement_pct'].mean())
                    result['median_replacement'] = float(valid_scm_pct['scm_replacement_pct'].median())
                    result['min_replacement'] = float(valid_scm_pct['scm_replacement_pct'].min())
                    result['max_replacement'] = float(valid_scm_pct['scm_replacement_pct'].max())
            
            results.append(result)
    
    # Generate SCM type distribution plot
    plt.figure(figsize=(12, 8))
    scm_by_dataset = {}
    
    # Collect SCM data for plotting
    for dataset in datasets:
        ds_df = df[df['dataset_name'] == dataset]
        scm_by_dataset[dataset] = ds_df['scm_primary_raw'].value_counts().to_dict()
    
    # Get all unique SCM types across all datasets
    all_scm_types = set()
    for dataset_scms in scm_by_dataset.values():
        all_scm_types.update(dataset_scms.keys())
    
    # Remove None values for plotting
    all_scm_types = [scm for scm in all_scm_types if pd.notna(scm)]
    
    # Create a DataFrame for plotting
    plot_data = []
    for dataset, scm_counts in scm_by_dataset.items():
        for scm_type in all_scm_types:
            count = scm_counts.get(scm_type, 0)
            if count > 0:  # Only include non-zero counts
                plot_data.append({
                    'Dataset': dataset,
                    'SCM Type': scm_type,
                    'Count': count
                })
    
    plot_df = pd.DataFrame(plot_data)
    
    if not plot_df.empty:
        # Create grouped bar plot
        plt.figure(figsize=(15, 8))
        ax = sns.barplot(x='SCM Type', y='Count', hue='Dataset', data=plot_df)
        plt.title('SCM Type Distribution Across Datasets', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save the plot
        plot_path = os.path.join(OUTPUT_DIR, 'scm_distribution_by_dataset.png')
        plt.savefig(plot_path, dpi=300)
        logger.info(f"Saved SCM distribution plot to {plot_path}")
    
    # Save detailed SCM analysis
    if results:
        import json
        
        # Create a custom JSON encoder to handle numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                import numpy as np
                if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                                  np.uint8, np.uint16, np.uint32, np.uint64)):
                    return int(obj)
                elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NumpyEncoder, self).default(obj)
        
        results_path = os.path.join(OUTPUT_DIR, 'scm_analysis_by_dataset.json')
        with open(results_path, 'w') as f:
            json.dump(results, f, cls=NumpyEncoder, indent=2)
        logger.info(f"Saved detailed SCM analysis to {results_path}")
    
    return results


if __name__ == '__main__':
    try:
        # Start time tracking
        start_time = datetime.now()
        logger.info('=' * 20 + ' DATASET VALIDATION ' + '=' * 20)
        logger.info(f"Validation started at {start_time}")
        
        # Fetch dataset metadata
        dataset_meta = fetch_dataset_metadata()
        logger.info(f"Found {len(dataset_meta)} datasets:")
        logger.info(dataset_meta[['name', 'mix_count']].to_string())
        
        # Fetch all mixes
        df = fetch_all_mixes()
        
        # Run validation checks
        completeness_results = validate_dataset_completeness(df)
        consistency_results = validate_data_consistency(df)
        scm_analysis = analyze_dataset_scm_types(df)
        
        # Calculate and log completion time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info('=' * 20 + ' VALIDATION COMPLETE ' + '=' * 20)
        logger.info(f"Validation completed in {duration:.1f} seconds")
        
        # List generated files
        files = os.listdir(OUTPUT_DIR)
        file_info = []
        for file in files:
            file_path = os.path.join(OUTPUT_DIR, file)
            size_kb = os.path.getsize(file_path) / 1024
            file_info.append(f"- {file} ({size_kb:.1f} KB)")
        
        logger.info("Generated files:")
        for info in file_info:
            logger.info(info)
        
    except Exception as e:
        logger.error(f"Validation failed with error: {str(e)}", exc_info=True)
        sys.exit(1)
