# Script to verify k_flag is being set correctly
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections
from cdb_app.models import ConcreteMix, Dataset

# Get DS5 dataset
ds5 = Dataset.objects.using('cdb').get(dataset_name='DS5')
print(f"\nDS5 Dataset Information:")
print(f"  Dataset ID: {ds5.dataset_id}")

# Get mixes with wb_k_reported values
mixes_with_k = ConcreteMix.objects.using('cdb').filter(
    dataset=ds5,
    wb_k_reported__isnull=False
).count()

# Get mixes with k_flag=True
mixes_with_flag = ConcreteMix.objects.using('cdb').filter(
    dataset=ds5,
    k_flag=True
).count()

# Get total count of mixes
total_mixes = ConcreteMix.objects.using('cdb').filter(dataset=ds5).count()

print(f"\nK-Value Implementation Statistics:")
print(f"  Total mixes: {total_mixes}")
print(f"  Mixes with wb_k_reported values: {mixes_with_k}")
print(f"  Mixes with k_flag=True: {mixes_with_flag}")

# Print sample of mixes to verify flag setting
sample_mixes = ConcreteMix.objects.using('cdb').filter(
    dataset=ds5
).order_by('?')[:10]  # Random sampling

print(f"\nSample Mixes:")
print(f"{'-'*60}")
print(f"{'Mix ID':<10} {'wb_k_reported':<15} {'k_flag':<8}")
print(f"{'-'*60}")

for mix in sample_mixes:
    wb_k_value = f"{mix.wb_k_reported:.3f}" if mix.wb_k_reported else "None"
    print(f"{mix.mix_code:<10} {wb_k_value:<15} {mix.k_flag}")
