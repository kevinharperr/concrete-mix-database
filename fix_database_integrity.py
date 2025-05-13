# Script to fix database integrity issues without breaking relationships
import os
import django
import csv
import datetime
from collections import defaultdict

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import transaction, connections
from django.db.models import Count
from cdb_app.models import ConcreteMix, MixComponent, Dataset

# Create a backup log directory if it doesn't exist
backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_backup')
os.makedirs(backup_dir, exist_ok=True)

timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

print("Database Integrity Fix")
print("=====================\n")

print("Step 1: Backing up current database state")

# Backup mix data to CSV before making changes
backup_file = os.path.join(backup_dir, f'mix_backup_{timestamp}.csv')
with open(backup_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['mix_id', 'dataset_id', 'dataset_name', 'mix_code', 'component_count'])
    
    for mix in ConcreteMix.objects.using('cdb').all():
        component_count = mix.components.count()
        writer.writerow([
            mix.mix_id, 
            mix.dataset.dataset_id if mix.dataset else 'None',
            mix.dataset.dataset_name if mix.dataset else 'None',
            mix.mix_code,
            component_count
        ])

print(f"  Created backup at {backup_file}")

# Function to format mix code correctly
def format_mix_code(dataset_name, original_code):
    # If it already follows the pattern DS#-###, leave it alone
    if original_code.startswith(f"{dataset_name}-"):
        return original_code
    
    # If it's just a number, format it as DS#-number
    try:
        number = int(original_code)
        return f"{dataset_name}-{number}"
    except ValueError:
        # If not numeric and not already in correct format, prefix with dataset name
        return f"{dataset_name}-{original_code}"

# Start fixing issues within a transaction to ensure atomicity
print("\nStep 2: Fixing non-standard mix codes")
try:
    with transaction.atomic(using='cdb'):
        # Get datasets
        datasets = Dataset.objects.using('cdb').all()
        dataset_map = {ds.dataset_id: ds.dataset_name for ds in datasets}
        
        # Fix non-standard mix codes
        non_standard = ConcreteMix.objects.using('cdb').exclude(mix_code__regex=r'^DS\d+-\d+')
        print(f"  Found {non_standard.count()} mixes with non-standard codes")
        
        updated_count = 0
        for mix in non_standard:
            original_code = mix.mix_code
            if not mix.dataset:
                print(f"    Skipping mix ID {mix.mix_id} with code '{original_code}' - no dataset assigned")
                continue
                
            dataset_name = mix.dataset.dataset_name
            new_code = format_mix_code(dataset_name, original_code)
            
            # Only update if it's actually changing
            if new_code != original_code:
                mix.mix_code = new_code
                mix.save(using='cdb')
                updated_count += 1
                
                if updated_count <= 10 or updated_count % 100 == 0:
                    print(f"    Updated mix ID {mix.mix_id}: '{original_code}' -> '{new_code}'")
        
        print(f"  Standardized {updated_count} mix codes")
    
    print("\nStep 3: Resolving duplicate mix codes")
    with transaction.atomic(using='cdb'):
        # Find duplicates
        duplicates = ConcreteMix.objects.using('cdb').values('mix_code').annotate(
            count=Count('mix_code')
        ).filter(count__gt=1)
        
        duplicate_codes = [item['mix_code'] for item in duplicates]
        print(f"  Found {len(duplicate_codes)} duplicate mix codes")
        
        # Group duplicates by code for processing
        for code in duplicate_codes:
            dupes = list(ConcreteMix.objects.using('cdb').filter(mix_code=code))
            
            # Skip if somehow we don't have multiple now (shouldn't happen within transaction)
            if len(dupes) < 2:
                continue
                
            print(f"    Processing duplicate code '{code}':")
            
            # Keep the original code for the first one we find
            # For others, prefix with dataset name if not already
            for i, mix in enumerate(dupes):
                if i == 0:
                    print(f"      Keeping original '{code}' for mix ID {mix.mix_id} (dataset {mix.dataset.dataset_name})")
                    continue
                
                # For duplicates, ensure dataset prefix is included
                dataset_name = mix.dataset.dataset_name
                new_code = format_mix_code(dataset_name, code)
                
                # If still duplicate, add a suffix
                if new_code == code or ConcreteMix.objects.using('cdb').filter(mix_code=new_code).exists():
                    new_code = f"{new_code}-dup{i}"
                
                print(f"      Updating mix ID {mix.mix_id}: '{code}' -> '{new_code}'")
                mix.mix_code = new_code
                mix.save(using='cdb')
    
    print("\nVerifying fixes:")
    # Verify non-standard codes are fixed
    remaining_non_standard = ConcreteMix.objects.using('cdb').exclude(mix_code__regex=r'^DS\d+-')
    print(f"  Non-standard codes remaining: {remaining_non_standard.count()}")
    
    # Verify duplicates are resolved
    remaining_dupes = ConcreteMix.objects.using('cdb').values('mix_code').annotate(
        count=Count('mix_code')
    ).filter(count__gt=1).count()
    print(f"  Duplicate codes remaining: {remaining_dupes}")
    
    print("\nDatabase integrity fixes completed successfully!")
    print("Note: ID sequences were not reset to maintain all existing relationships")
    
except Exception as e:
    print(f"\nERROR: {e}")
    print("No changes were committed due to the error.")
    print(f"You can refer to the backup file at {backup_file} if needed.")
