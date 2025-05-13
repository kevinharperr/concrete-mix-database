# Script to fix DS6 mix codes in the database
import os
import django
import sys
import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, Dataset
from django.db import transaction

# Create a timestamp for the changelog
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@transaction.atomic
def fix_ds6_mix_codes():
    print(f"[{timestamp}] Starting DS6 mix code correction")
    
    # Get DS6 dataset
    try:
        ds6_dataset = Dataset.objects.using("cdb").get(dataset_name="DS6")
    except Dataset.DoesNotExist:
        print("DS6 dataset not found in database!")
        return
    
    # Get mixes associated with this dataset
    ds6_mixes = ConcreteMix.objects.using("cdb").filter(dataset=ds6_dataset)
    total_mixes = len(ds6_mixes)
    print(f"Found {total_mixes} mixes associated with DS6 dataset")
    
    # Track changes for changelog
    fixed_mixes = 0
    unchanged_mixes = 0
    changelog_entries = []
    
    # Process each mix
    for mix in ds6_mixes:
        original_mix_code = mix.mix_code
        
        # Check if mix_code already has DS6 prefix
        if original_mix_code.startswith("DS6-"):
            unchanged_mixes += 1
            continue
            
        # Create new mix code with DS6 prefix
        new_mix_code = f"DS6-{original_mix_code}"
        
        # Check for potential conflicts
        conflicts = ConcreteMix.objects.using("cdb").filter(mix_code=new_mix_code).exclude(pk=mix.pk)
        if conflicts.exists():
            # Handle conflict by adding a suffix
            new_mix_code = f"DS6-{original_mix_code}-R"
            print(f"Conflict detected for {original_mix_code} -> using {new_mix_code} instead")
            
            # Check again for conflicts with the new code
            if ConcreteMix.objects.using("cdb").filter(mix_code=new_mix_code).exists():
                print(f"ERROR: Could not resolve conflict for {original_mix_code} - skipping")
                continue
        
        # Update the mix code
        mix.mix_code = new_mix_code
        mix.save(using="cdb")
        fixed_mixes += 1
        
        # Add to changelog
        changelog_entries.append(f"Changed mix code: {original_mix_code} -> {new_mix_code}")
        
        if fixed_mixes % 100 == 0:
            print(f"Processed {fixed_mixes} mixes so far...")
    
    print(f"\nSummary:")
    print(f"  Total DS6 mixes: {total_mixes}")
    print(f"  Fixed mixes: {fixed_mixes}")
    print(f"  Unchanged mixes: {unchanged_mixes}")
    
    # Create changelog entry
    changelog_content = f"\n## {timestamp} - DS6 Mix Code Standardization\n\n"
    changelog_content += f"* Fixed {fixed_mixes} mix codes to use standardized 'DS6-XXX' format\n"
    changelog_content += f"* Ensured all DS6 mixes are consistently named for proper identification\n"
    
    if fixed_mixes > 0:
        # Sample of changes (first 10)
        changelog_content += "\n### Sample of changes:\n\n"
        for entry in changelog_entries[:10]:
            changelog_content += f"* {entry}\n"
        
        if len(changelog_entries) > 10:
            changelog_content += f"* ... and {len(changelog_entries) - 10} more changes\n"
    
    return changelog_content

def update_changelog(changelog_entry):
    # Append to both changelogs
    master_changelog_path = "MASTER_CHANGELOG.md"
    ds6_changelog_path = "DS6_CHANGELOG.md"
    
    for path in [master_changelog_path, ds6_changelog_path]:
        try:
            with open(path, 'a') as f:
                f.write(changelog_entry)
            print(f"Updated {path} with changes")
        except Exception as e:
            print(f"Error updating {path}: {e}")

if __name__ == "__main__":
    print("Running DS6 Mix Code Fix")
    changelog_entry = fix_ds6_mix_codes()
    
    if changelog_entry:
        update_changelog(changelog_entry)
    
    print("Done!")
