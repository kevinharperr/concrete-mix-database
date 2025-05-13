# Script to analyze k-value implementation in more detail
import os
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections
from cdb_app.models import ConcreteMix, Dataset, MixComponent
from django.db.models import Sum, Q

# Get DS5 dataset
ds5 = Dataset.objects.using('cdb').get(dataset_name='DS5')
print(f"\nDS5 Dataset Information:")
print(f"  Dataset ID: {ds5.dataset_id}")

# Calculate some water/cement and water/binder ratios for sample mixes
sample_mixes = ConcreteMix.objects.using('cdb').filter(dataset=ds5).order_by('?')[:5]  # Random sampling

print(f"\nDetailed Analysis of Sample Mixes:")
print(f"{'-'*80}")
print(f"{'Mix ID':<10} {'w_b_ratio':<10} {'wb_k_reported':<15} {'Calculated W/B':<15} {'K Flag':<8}")
print(f"{'-'*80}")

for mix in sample_mixes:
    # Get components for this mix
    components = MixComponent.objects.using('cdb').filter(mix=mix)
    
    # Get cement, water and SCM components
    water = components.filter(
        material__material_class_id="WATER"
    ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
    
    cement = components.filter(
        material__material_class_id="CEMENT"
    ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
    
    scm = components.filter(
        Q(material__material_class_id="SCM") | 
        (Q(is_cementitious=True) & ~Q(material__material_class_id="CEMENT"))
    ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
    
    # Calculate binder total (cement + SCM)
    binder = cement + scm
    
    # Calculate water-to-binder ratio
    calculated_wb = water / binder if binder > 0 else None
    calculated_wb_str = f"{calculated_wb:.3f}" if calculated_wb else "N/A"
    
    # Format output
    w_b_ratio_str = f"{mix.w_b_ratio:.3f}" if mix.w_b_ratio else "None"
    wb_k_reported_str = f"{mix.wb_k_reported:.3f}" if mix.wb_k_reported else "None"
    
    print(f"{mix.mix_code:<10} {w_b_ratio_str:<10} {wb_k_reported_str:<15} {calculated_wb_str:<15} {mix.k_flag}")
    print(f"  Water: {water} kg/m³, Cement: {cement} kg/m³, SCM: {scm} kg/m³, Total Binder: {binder} kg/m³")

# Compare WB_RATIO_MISMATCH counts with and without our modification
print(f"\nAnalyzing WB_RATIO_MISMATCH counts:")
print(f"{'-'*80}")

# Count mixes where calculated_wb would differ from wb_k_reported
mismatch_count = 0
tolerance = Decimal('0.02')  # Same tolerance as in health check

for mix in ConcreteMix.objects.using('cdb').filter(dataset=ds5, wb_k_reported__isnull=False)[:100]:  # Sample first 100 for performance
    # Get components for this mix
    components = MixComponent.objects.using('cdb').filter(mix=mix)
    
    # Get cement, water and SCM components
    water = components.filter(material__material_class_id="WATER").aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
    cement = components.filter(material__material_class_id="CEMENT").aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
    scm = components.filter(Q(material__material_class_id="SCM") | (Q(is_cementitious=True) & ~Q(material__material_class_id="CEMENT"))).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
    
    # Calculate binder total and water-to-binder ratio
    binder = cement + scm
    calculated_wb = water / binder if binder > 0 else None
    
    if calculated_wb and mix.wb_k_reported:
        if abs(round(calculated_wb, 2) - round(mix.wb_k_reported, 2)) > tolerance:
            mismatch_count += 1

print(f"Sample count of mixes where calculated W/B != reported wb_k_reported: {mismatch_count}/100")
print(f"This suggests there would be ~{mismatch_count/100*1410} mismatches without our fix.")
