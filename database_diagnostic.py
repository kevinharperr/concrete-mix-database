# Script to diagnose database integrity issues
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections
from django.db.models import Count, Min, Max
from cdb_app.models import ConcreteMix, MixComponent, Material, Dataset

print("Database Integrity Diagnostic")
print("===========================\n")

# Check datasets
print("Dataset Information:")
datasets = Dataset.objects.using('cdb').all()
print(f"Total datasets: {len(datasets)}")
for dataset in datasets:
    mix_count = ConcreteMix.objects.using('cdb').filter(dataset=dataset).count()
    print(f"  ID: {dataset.dataset_id}, Name: {dataset.dataset_name}, Mix Count: {mix_count}")

# Check mix ID ranges and pattern issues
print("\nMix ID Analysis:")
mix_stats = ConcreteMix.objects.using('cdb').aggregate(min=Min('mix_id'), max=Max('mix_id'), count=Count('mix_id'))
print(f"  Mix ID range: {mix_stats['min']} to {mix_stats['max']} (Total: {mix_stats['count']} mixes)")

# Check for non-standard mix codes
pattern_issues = ConcreteMix.objects.using('cdb').exclude(mix_code__regex=r'^DS\d+-\d+')
print(f"  Mixes with non-standard codes: {pattern_issues.count()}")
if pattern_issues.exists():
    print("  Sample issues:")
    for mix in pattern_issues[:10]:
        print(f"    ID: {mix.mix_id}, Code: {mix.mix_code}, Dataset: {mix.dataset.dataset_name if mix.dataset else 'None'}")

# Check mix components
print("\nMix Component Analysis:")
components = MixComponent.objects.using('cdb').all()
total_components = components.count()
print(f"  Total components: {total_components}")

# Check orphaned components (no mix or material)
orphaned_components = MixComponent.objects.using('cdb').filter(mix__isnull=True).count()
print(f"  Orphaned components (no mix): {orphaned_components}")

orphaned_material = MixComponent.objects.using('cdb').filter(material__isnull=True).count()
print(f"  Orphaned components (no material): {orphaned_material}")

# Check dataset integrity (mixes without valid dataset)
print("\nData Integrity Issues:")
mixes_without_dataset = ConcreteMix.objects.using('cdb').filter(dataset__isnull=True).count()
print(f"  Mixes without dataset: {mixes_without_dataset}")

# Check for duplicate mix codes
print("\nDuplicate Detection:")
duplicates = ConcreteMix.objects.using('cdb').values('mix_code').annotate(count=Count('mix_code')).filter(count__gt=1)
print(f"  Mix codes with duplicates: {duplicates.count()}")
if duplicates.exists():
    print("  Sample duplicates:")
    for dup in duplicates[:5]:
        code = dup['mix_code']
        instances = ConcreteMix.objects.using('cdb').filter(mix_code=code)
        print(f"    Code '{code}' appears {instances.count()} times:")
        for inst in instances:
            print(f"      ID: {inst.mix_id}, Dataset: {inst.dataset.dataset_name if inst.dataset else 'None'}")
