# detailed_verification.py
# Script to verify the imported data with more specific checks

import os
import django
import collections

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb
from django.db.models import Count, Avg, Max, Min, F, FloatField
from django.db.models.functions import Cast

# Check 3 specific mixes (beginning, middle, end)
mix_codes = ['DS1-1', 'DS1-515', 'DS1-1030']
print(f"\nSample Mixes Verification:\n{'-'*30}")

for code in mix_codes:
    try:
        mix = cdb.ConcreteMix.objects.using("cdb").get(mix_code=code)
        components = cdb.MixComponent.objects.using("cdb").filter(mix=mix)
        results = cdb.PerformanceResult.objects.using("cdb").filter(mix=mix)
        
        print(f"\nMix {code}:")
        print(f"  W/C Ratio: {mix.w_c_ratio}")
        print(f"  Number of components: {components.count()}")
        print(f"  Components:")
        
        for comp in components:
            material = comp.material
            print(f"    - {material.specific_name} ({material.material_class_id}): {comp.dosage_kg_m3} kg/m³")
            
        print(f"  Performance Results:")
        for result in results:
            print(f"    - {result.category} test: {result.value_num} MPa at {result.age_days} days")
    
    except cdb.ConcreteMix.DoesNotExist:
        print(f"Mix {code} not found")
        
# Average MPa query
avg_mpa = cdb.PerformanceResult.objects.using("cdb").filter(
    mix__dataset__dataset_name="DS1",
    test_method_id=2,  # Compressive strength
    category="hardened"
).aggregate(Avg('value_num'))['value_num__avg']

print(f"\n\nSmoke Test Queries:\n{'-'*30}")
print(f"Average compressive strength: {avg_mpa:.2f} MPa")

# W/C ratio distribution
w_c_query = cdb.ConcreteMix.objects.using("cdb").filter(
    dataset__dataset_name="DS1",
    w_c_ratio__isnull=False
).values_list('w_c_ratio', flat=True)

w_c_values = list(w_c_query)

print(f"W/C ratio stats:")
print(f"  Count: {len(w_c_values)}")
print(f"  Min: {min(w_c_values):.2f}")
print(f"  Max: {max(w_c_values):.2f}")
print(f"  Mean: {sum(w_c_values)/len(w_c_values):.2f}")

# Basic histogram stats of w/c ratio
w_c_bins = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0]
w_c_hist = [0] * (len(w_c_bins)-1)

for val in w_c_values:
    for i in range(len(w_c_bins)-1):
        if w_c_bins[i] <= val < w_c_bins[i+1]:
            w_c_hist[i] += 1
            break

print(f"\nW/C ratio distribution:")
for i in range(len(w_c_hist)):
    bin_start = w_c_bins[i]
    bin_end = w_c_bins[i+1]
    count = w_c_hist[i]
    print(f"  {bin_start:.1f}-{bin_end:.1f}: {count} mixes")

print("\nVerification complete - now check in pgAdmin/Django admin!")
print("\nDon't forget to run: pg_dump -Fc -d cdb > cdb_after_DS1.dump")
