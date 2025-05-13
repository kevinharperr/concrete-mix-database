import os
import sys
import csv
import django
from decimal import Decimal
from collections import defaultdict

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from cdb_app import models as cdb

def generate_health_flags(dataset_name='DS6', output_file='ds6_health_flags.csv'):
    """Generate health flags for DS6 dataset and output to CSV"""
    print(f"Generating health flags for {dataset_name} dataset...")
    
    # Get the dataset record
    try:
        dataset = cdb.Dataset.objects.using('cdb').get(dataset_name=dataset_name)
        print(f"Found {dataset_name} dataset: {dataset}")
    except cdb.Dataset.DoesNotExist:
        print(f"Error: {dataset_name} dataset not found")
        return
    
    # Get all mixes for the dataset
    mixes = cdb.ConcreteMix.objects.using('cdb').filter(dataset=dataset)
    print(f"Found {mixes.count()} mixes to analyze")
    
    # Prepare CSV rows
    csv_rows = []
    
    # Iterate through each mix and evaluate health flags
    for mix in mixes:
        # Basic mix info
        mix_data = {
            'mix_code': mix.mix_code,
            'dataset': dataset_name
        }
        
        # Initialize all flags to 0 (good)
        mix_data.update({
            'flag_missing_cement': 0,
            'flag_missing_water': 0,
            'flag_missing_aggregate': 0,
            'flag_missing_wcr': 0,
            'flag_zero_cement': 0,
            'flag_zero_water': 0,
            'flag_zero_aggregate': 0,
            'flag_invalid_wcr': 0,
            'flag_missing_28d_strength': 0,
            'flag_missing_slump': 0
        })
        
        # Check components
        components = cdb.MixComponent.objects.using('cdb').filter(mix=mix)
        
        # Track materials by type
        has_cement = False
        has_water = False
        has_aggregate = False
        total_cement = Decimal('0.0')
        total_water = Decimal('0.0')
        total_aggregate = Decimal('0.0')
        
        for comp in components:
            material_class = comp.material.material_class.class_code
            # Check for cementitious materials (CEMENT or SCM)
            if material_class == 'CEMENT' or material_class == 'SCM':
                has_cement = True
                total_cement += comp.dosage_kg_m3 or Decimal('0.0')
            elif material_class == 'WATER':
                has_water = True
                total_water += comp.dosage_kg_m3 or Decimal('0.0')
            elif material_class.startswith('AGGR'):
                has_aggregate = True
                total_aggregate += comp.dosage_kg_m3 or Decimal('0.0')
        
        # Set component flags
        if not has_cement:
            mix_data['flag_missing_cement'] = 1
        if not has_water:
            mix_data['flag_missing_water'] = 1
        if not has_aggregate:
            mix_data['flag_missing_aggregate'] = 1
            
        # Set zero quantity flags
        if has_cement and total_cement == 0:
            mix_data['flag_zero_cement'] = 1
        if has_water and total_water == 0:
            mix_data['flag_zero_water'] = 1
        if has_aggregate and total_aggregate == 0:
            mix_data['flag_zero_aggregate'] = 1
        
        # Check w/c ratio
        if mix.w_c_ratio is None:
            mix_data['flag_missing_wcr'] = 1
        elif mix.w_c_ratio <= 0 or mix.w_c_ratio > 2.0:  # Typical range for w/c ratio is 0.3-0.7
            mix_data['flag_invalid_wcr'] = 1
            
        # Check for performance results
        has_28d_strength = False
        has_slump = False
        
        results = cdb.PerformanceResult.objects.using('cdb').filter(mix=mix)
        for result in results:
            # Check for 28-day compressive strength results
            if result.category == 'hardened' and result.age_days == 28:
                has_28d_strength = True
            # Check for fresh concrete slump results
            elif result.category == 'fresh':
                has_slump = True
        
        if not has_28d_strength:
            mix_data['flag_missing_28d_strength'] = 1
        if not has_slump:
            mix_data['flag_missing_slump'] = 1
        
        # Add data quality score (sum of all flags, 0 is perfect)
        flags_sum = sum(value for key, value in mix_data.items() if key.startswith('flag_'))
        mix_data['data_quality_score'] = 10 - flags_sum  # 10 is perfect, 0 is worst
        
        # Add row
        csv_rows.append(mix_data)
    
    # Calculate statistics
    total_mixes = len(csv_rows)
    flag_counts = defaultdict(int)
    quality_distribution = defaultdict(int)
    
    for row in csv_rows:
        for key, value in row.items():
            if key.startswith('flag_') and value == 1:
                flag_counts[key] += 1
        quality_distribution[row['data_quality_score']] += 1
    
    # Print statistics
    print("\nHealth Flag Statistics:")
    print(f"Total mixes analyzed: {total_mixes}")
    for flag, count in flag_counts.items():
        percentage = (count / total_mixes) * 100 if total_mixes > 0 else 0
        print(f"{flag}: {count} mixes ({percentage:.1f}%)")
    
    print("\nData Quality Score Distribution:")
    for score in sorted(quality_distribution.keys(), reverse=True):
        count = quality_distribution[score]
        percentage = (count / total_mixes) * 100 if total_mixes > 0 else 0
        print(f"Score {score}: {count} mixes ({percentage:.1f}%)")
    
    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        fieldnames = [
            'mix_code', 'dataset', 
            'flag_missing_cement', 'flag_missing_water', 'flag_missing_aggregate',
            'flag_missing_wcr', 'flag_zero_cement', 'flag_zero_water', 'flag_zero_aggregate',
            'flag_invalid_wcr', 'flag_missing_28d_strength', 'flag_missing_slump',
            'data_quality_score'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    
    print(f"\nHealth flags written to {output_file}")

if __name__ == "__main__":
    generate_health_flags()
