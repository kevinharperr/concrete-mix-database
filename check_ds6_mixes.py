# Script to check DS6 mixes in the database
import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, Material, MixComponent, Dataset
from django.db import transaction

def check_ds6_mixes():
    print("\nChecking all mixes in database:")
    all_mixes = ConcreteMix.objects.using("cdb").all()
    print(f"Total mixes in database: {len(all_mixes)}")
    
    # Group by prefix to detect pattern
    prefix_counts = {}
    for mix in all_mixes:
        # Get first characters until hyphen or underscore
        if '-' in mix.mix_code:
            prefix = mix.mix_code.split('-')[0]
        elif '_' in mix.mix_code:
            prefix = mix.mix_code.split('_')[0]
        else:
            prefix = mix.mix_code
        
        if prefix not in prefix_counts:
            prefix_counts[prefix] = 0
        prefix_counts[prefix] += 1
    
    print("\nMix code prefixes found:")
    for prefix, count in prefix_counts.items():
        print(f"  {prefix}: {count} mixes")
    
    # Look for any DS6 related mixes using various patterns
    ds6_related = ConcreteMix.objects.using("cdb").filter(mix_code__icontains="DS6")
    print(f"\nMixes containing 'DS6' anywhere in mix_code: {len(ds6_related)}")
    
    if ds6_related:
        print("Sample of mix codes:")
        for mix in ds6_related[:10]:  # Show first 10
            print(f"  {mix.mix_code}")
            # Check components
            components = MixComponent.objects.using("cdb").filter(mix=mix)
            print(f"    Components: {len(components)}")
    
    # Check dataset
    try:
        ds6_dataset = Dataset.objects.using("cdb").get(dataset_name="DS6")
        print(f"\nFound DS6 dataset: {ds6_dataset.dataset_name}")
        
        # Get mixes associated with this dataset
        dataset_mixes = ConcreteMix.objects.using("cdb").filter(dataset=ds6_dataset)
        print(f"Mixes associated with DS6 dataset: {len(dataset_mixes)}")
        
        if dataset_mixes:
            print("Sample of DS6 dataset mix codes:")
            for mix in dataset_mixes[:10]:  # Show first 10
                print(f"  {mix.mix_code}")
                
    except Dataset.DoesNotExist:
        print("\nDS6 dataset not found in database")

if __name__ == "__main__":
    print("Running DS6 Database Check")
    check_ds6_mixes()
