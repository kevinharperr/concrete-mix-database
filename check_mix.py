# Script to check mix components and calculate w/b ratio

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, MixComponent

# Check multiple mixes with potentially high w/b ratios
# Check one of the previously problematic mixes
mix_ids = [13560]  # This had a w/b ratio of 1.419, now should be ~0.568

def check_mix(mix_id):
    try:
        mix = ConcreteMix.objects.get(mix_id=mix_id)
        components = MixComponent.objects.filter(mix=mix).select_related('material')
        
        print(f"\n============= Mix ID: {mix.mix_id} =============")
        print(f"Mix Code: {mix.mix_code}")
        print(f"W/B Ratio in DB: {mix.w_b_ratio}")
        print(f"W/C Ratio in DB: {mix.w_c_ratio}")
        
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
                print(f"  Checking subtype: '{subtype_lower}'")
                
                # First check for exact matches on common abbreviations
                if subtype_lower in ['fa', 'sf', 'ggbs', 'cfa']:
                    is_reactive = True
                    if subtype_lower == 'fa':
                        print(f"  Identified as Fly Ash (reactive)")
                    elif subtype_lower == 'sf':
                        print(f"  Identified as Silica Fume (reactive)")
                    elif subtype_lower == 'ggbs':
                        print(f"  Identified as GGBS (reactive)")
                    elif subtype_lower == 'cfa':
                        print(f"  Identified as Coal Fly Ash (reactive)")
                    
                # Then check for substring matches for longer names
                elif any(keyword in subtype_lower for keyword in [
                    'fly_ash', 'flyash', 'fly ash', 'coal fly ash',
                    'silica_fume', 'silicafume', 'silica fume',
                    'ground_granulated_blast_furnace_slag', 'ground granulated blast furnace slag',
                    'pozzolan', 'natural_pozzolan', 'natural pozzolan'
                ]):
                    is_reactive = True
                    
                    if any(keyword in subtype_lower for keyword in ['fly_ash', 'flyash', 'fly ash', 'coal fly ash']):
                        print(f"  Identified as Fly Ash (reactive)")
                    elif any(keyword in subtype_lower for keyword in ['silica_fume', 'silicafume', 'silica fume']):
                        print(f"  Identified as Silica Fume (reactive)")
                    elif any(keyword in subtype_lower for keyword in ['ground_granulated_blast_furnace_slag', 'ground granulated blast furnace slag', 'ggbs']):
                        print(f"  Identified as GGBS (reactive)")
                    elif any(keyword in subtype_lower for keyword in ['pozzolan', 'natural_pozzolan', 'natural pozzolan']):
                        print(f"  Identified as Natural Pozzolan (reactive)")
                    
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
            
            # Compare stored and calculated values
            if mix.w_b_ratio:
                diff = abs(float(mix.w_b_ratio) - calculated_wb)
                if diff > 0.01:
                    print(f"MISMATCH: DB value ({mix.w_b_ratio}) differs from calculated ({calculated_wb:.3f}) by {diff:.3f}")
            
            # Calculate w/c ratio for comparison
            if cement_content > 0:
                calculated_wc = water_content / cement_content
                print(f"Calculated w/c ratio: {calculated_wc:.3f}")
        else:
            print("\nCannot calculate w/b ratio: missing water or binder components")
    except ConcreteMix.DoesNotExist:
        print(f"Mix ID {mix_id} does not exist in the database.")
    except Exception as e:
        print(f"Error checking mix {mix_id}: {str(e)}")

# Check each mix
for mix_id in mix_ids:
    check_mix(mix_id)
