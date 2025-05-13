# inspect_mix_ratios.py
# Script to inspect mix ratios for a specific mix

import os
import django
from decimal import Decimal

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb
from django.db.models import Sum, Q

def inspect_mix(mix_code):
    try:
        # Get the mix
        mix = cdb.ConcreteMix.objects.using("cdb").get(mix_code=mix_code)
        print(f"\nMix: {mix.mix_code}")
        print(f"Reported W/C ratio: {mix.w_c_ratio}")
        print(f"Reported W/B ratio: {mix.w_b_ratio}")
        
        # Get components
        components = cdb.MixComponent.objects.using("cdb").filter(mix=mix)
        
        # Print all components
        print(f"\nComponents:")
        for comp in components:
            print(f"  {comp.material} - {comp.dosage_kg_m3} kg/m³ - Is Cementitious: {comp.is_cementitious}")
        
        # Calculate water content
        water = components.filter(
            material__material_class_id="WATER"
        ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
        
        # Calculate cement content
        cement = components.filter(
            material__material_class_id="CEMENT"
        ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
        
        # Calculate SCM content - using is_cementitious flag
        scm_by_flag = components.filter(
            Q(is_cementitious=True) & ~Q(material__material_class_id="CEMENT")
        ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
        
        # Alternative: Calculate SCM content - using class code
        scm_by_class = components.filter(
            material__material_class_id="SCM"
        ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
        
        # Calculate total binder content
        binder_by_flag = cement + scm_by_flag
        binder_by_class = cement + scm_by_class
        
        # Calculate ratios
        wc_ratio = water / cement if cement > 0 else Decimal('0')
        wb_ratio_by_flag = water / binder_by_flag if binder_by_flag > 0 else Decimal('0')
        wb_ratio_by_class = water / binder_by_class if binder_by_class > 0 else Decimal('0')
        
        print(f"\nCalculated Values:")
        print(f"Water: {water} kg/m³")
        print(f"Cement: {cement} kg/m³")
        print(f"SCM (by is_cementitious flag): {scm_by_flag} kg/m³")
        print(f"SCM (by SCM class): {scm_by_class} kg/m³")
        print(f"Total Binder (by flag): {binder_by_flag} kg/m³")
        print(f"Total Binder (by class): {binder_by_class} kg/m³")
        print(f"\nCalculated W/C ratio: {wc_ratio:.2f}")
        print(f"Calculated W/B ratio (by flag): {wb_ratio_by_flag:.2f}")
        print(f"Calculated W/B ratio (by class): {wb_ratio_by_class:.2f}")
        
        # Check match with reported values
        wc_match = abs(wc_ratio - mix.w_c_ratio) <= Decimal('0.02') if mix.w_c_ratio else None
        wb_match_flag = abs(wb_ratio_by_flag - mix.w_b_ratio) <= Decimal('0.02') if mix.w_b_ratio else None
        wb_match_class = abs(wb_ratio_by_class - mix.w_b_ratio) <= Decimal('0.02') if mix.w_b_ratio else None
        
        print(f"\nComparison:")
        print(f"W/C ratio matches: {wc_match}")
        print(f"W/B ratio matches (by flag): {wb_match_flag}")
        print(f"W/B ratio matches (by class): {wb_match_class}")
        
    except cdb.ConcreteMix.DoesNotExist:
        print(f"Mix {mix_code} not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    mix_code = "DS1-5"
    inspect_mix(mix_code)
