# Script to check k-value fields in the DS5 dataset
import os
import django
from decimal import Decimal

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

# Get mixes with both w_b_ratio and wb_k_reported
mixes_with_both = ConcreteMix.objects.using('cdb').filter(
    dataset=ds5,
    w_b_ratio__isnull=False,
    wb_k_reported__isnull=False
).count()

print(f"\nK-Value Statistics:")
print(f"  Mixes with wb_k_reported values: {mixes_with_k}")
print(f"  Mixes with k_flag=True: {mixes_with_flag}")
print(f"  Mixes with both w_b_ratio and wb_k_reported: {mixes_with_both}")

# Get sample of mixes with both values for comparison
sample_mixes = ConcreteMix.objects.using('cdb').filter(
    dataset=ds5,
    w_b_ratio__isnull=False,
    wb_k_reported__isnull=False
).order_by('?')[:5]  # Random sampling

print(f"\nSample Comparison of w_b_ratio vs wb_k_reported:")
print(f"{'-'*60}")
print(f"{'Mix ID':<10} {'w_b_ratio':<10} {'wb_k_reported':<15} {'Difference':<10}")
print(f"{'-'*60}")

for mix in sample_mixes:
    diff = abs(mix.w_b_ratio - mix.wb_k_reported) if (mix.w_b_ratio and mix.wb_k_reported) else 'N/A'
    if diff != 'N/A':
        diff = round(diff, 3)
    print(f"{mix.mix_code:<10} {mix.w_b_ratio:<10} {mix.wb_k_reported:<15} {diff}")
