# Script to check mixes that still have high w/b ratios

import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, MixComponent
from decimal import Decimal

# Load high w/b ratio mixes from CSV
df = pd.read_csv('cdb_database_wb_ratios.csv')
high_wb_mix_ids = df[df['w_b_ratio'] > 1.0]['mix_id'].tolist()

print(f"Found {len(high_wb_mix_ids)} mixes with w/b ratio > 1.0")

# Check some of these mixes
sample_ids = high_wb_mix_ids[:5]  # Check first 5

def check_mix_components(mix_id):
    try:
        mix = ConcreteMix.objects.get(mix_id=mix_id)
        components = MixComponent.objects.filter(mix=mix).select_related('material')
        
        print(f"\n============= Mix ID: {mix.mix_id} =============")
        print(f"Mix Code: {mix.mix_code}")
        print(f"W/B Ratio: {mix.w_b_ratio}")
        print(f"K-Flag: {mix.k_flag}")
        print(f"W/B with K-Value reported: {mix.wb_k_reported}")
        
        water_content = 0
        cement_content = 0
        reactive_scm_content = 0
        
        if not components.exists():
            print("No components found for this mix!")
            return
            
        print("Components:")
        for comp in components:
            material_class = comp.material.material_class.class_code
            subtype = comp.material.subtype_code or ''
            dosage = comp.dosage_kg_m3
            
            print(f"{material_class} - {subtype}: {dosage} kg/m3")
            
            # Track material contents for w/b calculation
            if material_class == 'WATER':
                water_content += dosage
            elif material_class == 'CEMENT':
                cement_content += dosage
            elif material_class == 'SCM':
                # Check if this is a reactive SCM
                is_reactive = False
                
                # Check for reactive SCMs
                subtype_lower = subtype.lower()
                
                # First check for exact matches on common abbreviations
                if subtype_lower in ['fa', 'sf', 'ggbs', 'cfa']:
                    is_reactive = True
                    print(f"  Identified as Reactive SCM")
                # Then check for substring matches for longer names
                elif any(keyword in subtype_lower for keyword in [
                    'fly_ash', 'flyash', 'fly ash', 'coal fly ash',
                    'silica_fume', 'silicafume', 'silica fume',
                    'ground_granulated_blast_furnace_slag', 'ground granulated blast furnace slag',
                    'pozzolan', 'natural_pozzolan', 'natural pozzolan'
                ]):
                    is_reactive = True
                    print(f"  Identified as Reactive SCM")
                    
                # Specifically exclude limestone powder
                if any(keyword in subtype.lower() for keyword in [
                    'limestone', 'limestone_powder', 'limestone powder'
                ]):
                    is_reactive = False
                    
                if is_reactive:
                    reactive_scm_content += dosage
                    print(f"  [Counted as reactive SCM]")
        
        # Calculate binder content
        binder_content = cement_content + reactive_scm_content
        
        # Calculate w/b ratio
        if binder_content > 0 and water_content > 0:
            calculated_wb = water_content / binder_content
            print(f"\nCalculated values:")
            print(f"Water content: {water_content} kg/m3")
            print(f"Cement content: {cement_content} kg/m3")
            print(f"Reactive SCM content: {reactive_scm_content} kg/m3")
            print(f"Total binder content: {binder_content} kg/m3")
            print(f"Calculated w/b ratio: {calculated_wb:.3f}")
            
            # Compare with DB value
            if mix.w_b_ratio:
                diff = abs(float(calculated_wb) - float(mix.w_b_ratio))
                print(f"Difference from DB value: {diff:.3f}")
                if diff > 0.01:
                    print(f"SIGNIFICANT DIFFERENCE: DB={mix.w_b_ratio}, Calculated={calculated_wb:.3f}")
        else:
            print("\nCannot calculate w/b ratio: missing water or binder components")
    except Exception as e:
        print(f"Error checking mix {mix_id}: {str(e)}")

# Check each mix
print("\nChecking sample mixes...")
for mix_id in sample_ids:
    check_mix_components(mix_id)
