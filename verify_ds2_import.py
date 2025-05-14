#!/usr/bin/env python
"""
Specific validation script for DS2 dataset to identify inconsistencies
between the original CSV data and database records.
"""
import os
import sys
import django
import pandas as pd
from decimal import Decimal
import re

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from django.db.models import Sum, Count
from cdb_app.models import ConcreteMix, MixComponent, Material

def get_mix_component_dosage(mix, material_class=None, subtype=None):
    """Get total dosage of components matching criteria in a mix."""
    query = MixComponent.objects.filter(mix=mix)
    
    if material_class:
        query = query.filter(material__material_class__class_code=material_class)
    
    if subtype:
        query = query.filter(material__subtype_code=subtype)
    
    result = query.aggregate(total=Sum('dosage_kg_m3'))['total']
    return result or Decimal('0')

def extract_mix_number(mix_code):
    """Extract mix number from mix code like 'DS2-734'."""
    if not mix_code:
        return None
    
    # Try pattern DS2-{number} (for dataset_id=9)
    pattern = r'DS2-(\d+)'
    match = re.match(pattern, mix_code)
    if match:
        return int(match.group(1))
    
    # Alternative pattern DS9-{number}
    pattern = r'DS9-(\d+)'
    match = re.match(pattern, mix_code)
    if match:
        return int(match.group(1))
    
    return None

def compare_mix_with_csv(mix, df_row):
    """Compare database mix with CSV row and return discrepancies."""
    discrepancies = []
    
    # Check cement content
    db_cement = get_mix_component_dosage(mix, 'CEMENT')
    csv_cement = df_row.get('Cement Content kg/m^3')
    if abs(float(db_cement) - float(csv_cement)) > 1.0:  # Allow small differences
        discrepancies.append(f"Cement: DB={db_cement}, CSV={csv_cement}")
    
    # Check water content
    # Since water content isn't directly in CSV, calculate from w/c ratio
    db_water = get_mix_component_dosage(mix, 'WATER')
    w_c_ratio = df_row.get('Eff. W/C ratio')
    calculated_water = float(csv_cement) * float(w_c_ratio)
    if abs(float(db_water) - calculated_water) > 5.0:  # Allow larger tolerance for calculated values
        discrepancies.append(f"Water: DB={db_water}, CSV~{calculated_water}")
    
    # Check W/C ratio
    db_wc = mix.w_c_ratio
    csv_wc = df_row.get('Eff. W/C ratio')
    if db_wc and csv_wc and abs(float(db_wc) - float(csv_wc)) > 0.01:
        discrepancies.append(f"W/C ratio: DB={db_wc}, CSV={csv_wc}")
    
    # Check NCA content
    db_nca = get_mix_component_dosage(mix, 'AGGR_C', 'NCA')
    csv_nca = df_row.get('NCA Content')
    if csv_nca and abs(float(db_nca) - float(csv_nca)) > 5.0:
        discrepancies.append(f"NCA: DB={db_nca}, CSV={csv_nca}")
    
    # Check NFA content
    db_nfa = get_mix_component_dosage(mix, 'AGGR_F', 'NFA')
    csv_nfa = df_row.get('NFA Content')
    if csv_nfa and abs(float(db_nfa) - float(csv_nfa)) > 5.0:
        discrepancies.append(f"NFA: DB={db_nfa}, CSV={csv_nfa}")
    
    # Check RCA content
    db_rca = get_mix_component_dosage(mix, 'AGGR_C', 'RCA')
    csv_rca = df_row.get('RCA Content') 
    if csv_rca and abs(float(db_rca) - float(csv_rca)) > 5.0:
        discrepancies.append(f"RCA: DB={db_rca}, CSV={csv_rca}")
    
    # Check for missing components (RCA, NFA, NCA)
    if csv_nca and float(csv_nca) > 0 and float(db_nca) == 0:
        discrepancies.append(f"Missing NCA component: CSV has {csv_nca} kg/m³")
    if csv_nfa and float(csv_nfa) > 0 and float(db_nfa) == 0:
        discrepancies.append(f"Missing NFA component: CSV has {csv_nfa} kg/m³")
    if csv_rca and float(csv_rca) > 0 and float(db_rca) == 0:
        discrepancies.append(f"Missing RCA component: CSV has {csv_rca} kg/m³")
    
    return discrepancies

def find_matching_csv_mix(db_mix_number, cement_content, water_content, df):
    """Find a matching mix in the CSV by looking at cement and water content."""
    best_match = None
    best_score = float('inf')
    
    for _, row in df.iterrows():
        csv_cement = row.get('Cement Content kg/m^3')
        csv_wc = row.get('Eff. W/C ratio')
        
        if pd.isna(csv_cement) or pd.isna(csv_wc):
            continue
            
        csv_water = float(csv_cement) * float(csv_wc)
        
        # Calculate a match score based on cement and water content similarity
        # Lower score = better match
        cement_diff = abs(float(cement_content) - float(csv_cement))
        water_diff = abs(float(water_content) - csv_water)
        
        score = cement_diff + water_diff
        
        if score < best_score:
            best_score = score
            best_match = (row, score)
    
    # Only return matches with a good score
    if best_match and best_match[1] < 20:  # Reasonable threshold for total difference
        return best_match[0]
    
    return None

def main():
    # Path to DS2 dataset
    ds2_path = os.path.join('etl', 'ds2.csv')
    
    if not os.path.exists(ds2_path):
        print(f"DS2 dataset file not found: {ds2_path}")
        return
    
    # Load dataset
    ds2_df = pd.read_csv(ds2_path)
    print(f"Loaded DS2 dataset with {len(ds2_df)} records")
    
    # Get DS2 mixes from database
    db_mixes = ConcreteMix.objects.filter(dataset_id=9)
    print(f"Found {db_mixes.count()} mixes in database with dataset_id=9")
    
    # Track mismatches
    mismatches = []
    potential_swaps = []
    
    # Process each mix
    for mix in db_mixes:
        mix_number = extract_mix_number(mix.mix_code)
        if not mix_number:
            print(f"Could not extract mix number from {mix.mix_code}")
            continue
        
        # Try to find this mix in the CSV
        csv_rows = ds2_df[ds2_df['Mix Number'] == mix_number]
        
        if len(csv_rows) == 0:
            # This mix number doesn't exist in CSV
            # Try to find a potential match based on composition
            cement_content = get_mix_component_dosage(mix, 'CEMENT')
            water_content = get_mix_component_dosage(mix, 'WATER')
            
            potential_match = find_matching_csv_mix(mix_number, cement_content, water_content, ds2_df)
            
            if potential_match is not None:
                match_mix_number = potential_match['Mix Number']
                potential_swaps.append({
                    'db_mix_id': mix.mix_id,
                    'db_mix_code': mix.mix_code,
                    'extracted_number': mix_number,
                    'potential_match': match_mix_number,
                    'db_cement': cement_content,
                    'db_water': water_content,
                    'csv_cement': potential_match['Cement Content kg/m^3'],
                    'csv_wc': potential_match['Eff. W/C ratio']
                })
                print(f"Mix {mix.mix_code} (ID: {mix.mix_id}) not found in CSV but potentially matches Mix #{match_mix_number}")
            else:
                print(f"Mix {mix.mix_code} (ID: {mix.mix_id}) not found in CSV and no potential match identified")
        else:
            # Found the mix in CSV, compare values
            csv_row = csv_rows.iloc[0]
            discrepancies = compare_mix_with_csv(mix, csv_row)
            
            if discrepancies:
                mismatches.append({
                    'mix_id': mix.mix_id,
                    'mix_code': mix.mix_code,
                    'mix_number': mix_number,
                    'discrepancies': discrepancies
                })
    
    # Display results
    print(f"\nFound {len(mismatches)} mixes with discrepancies")
    if mismatches:
        print("\nMixes with discrepancies:")
        for m in mismatches:
            print(f"\nMix {m['mix_code']} (ID: {m['mix_id']}):")
            for d in m['discrepancies']:
                print(f"  - {d}")
    
    print(f"\nFound {len(potential_swaps)} potential mix number swaps")
    if potential_swaps:
        print("\nPotential mix number swaps (possible import issues):")
        for swap in potential_swaps:
            print(f"\nDB Mix {swap['db_mix_code']} (ID: {swap['db_mix_id']}) appears to contain data from CSV Mix #{swap['potential_match']}")
            print(f"  DB values: Cement={swap['db_cement']} kg/m³, Water={swap['db_water']} kg/m³")
            print(f"  CSV values: Cement={swap['csv_cement']} kg/m³, W/C ratio={swap['csv_wc']}")
    
    # Specific check for Mix 8110
    try:
        mix_8110 = ConcreteMix.objects.get(mix_id=8110)
        print("\nDetailed Analysis of Mix 8110:")
        print(f"Mix Code: {mix_8110.mix_code}")
        extracted_number = extract_mix_number(mix_8110.mix_code)
        print(f"Extracted Number: {extracted_number}")
        
        # Look for mix 734 in CSV
        csv_734 = ds2_df[ds2_df['Mix Number'] == 734]
        if len(csv_734) > 0:
            csv_734_row = csv_734.iloc[0]
            print("\nCSV Data for Mix #734:")
            print(f"Cement: {csv_734_row['Cement Content kg/m^3']} kg/m³")
            print(f"W/C ratio: {csv_734_row['Eff. W/C ratio']}")
            print(f"NCA: {csv_734_row['NCA Content']} kg/m³")
            print(f"NFA: {csv_734_row['NFA Content']} kg/m³")
            print(f"RCA: {csv_734_row['RCA Content']} kg/m³")
        
        # Look for mix 979 in CSV
        csv_979 = ds2_df[ds2_df['Mix Number'] == 979]
        if len(csv_979) > 0:
            csv_979_row = csv_979.iloc[0]
            print("\nCSV Data for Mix #979:")
            print(f"Cement: {csv_979_row['Cement Content kg/m^3']} kg/m³")
            print(f"W/C ratio: {csv_979_row['Eff. W/C ratio']}")
            print(f"NCA: {csv_979_row.get('NCA Content', 'N/A')} kg/m³")
            print(f"NFA: {csv_979_row.get('NFA Content', 'N/A')} kg/m³")
            print(f"RCA: {csv_979_row.get('RCA Content', 'N/A')} kg/m³")
        
        # Database values for 8110
        print("\nDatabase Values for Mix 8110:")
        print(f"Cement: {get_mix_component_dosage(mix_8110, 'CEMENT')} kg/m³")
        print(f"Water: {get_mix_component_dosage(mix_8110, 'WATER')} kg/m³")
        print(f"NCA: {get_mix_component_dosage(mix_8110, 'AGGR_C', 'NCA')} kg/m³")
        print(f"NFA: {get_mix_component_dosage(mix_8110, 'AGGR_F', 'NFA')} kg/m³")
        print(f"RCA: {get_mix_component_dosage(mix_8110, 'AGGR_C', 'RCA')} kg/m³")
        print(f"W/C ratio: {mix_8110.w_c_ratio}")
        print(f"W/B ratio: {mix_8110.w_b_ratio}")
        
        # List components
        components = MixComponent.objects.filter(mix=mix_8110).select_related('material')
        print("\nAll Components:")
        for comp in components:
            material_class = comp.material.material_class.class_code if comp.material.material_class else "None"
            print(f"  {material_class} - {comp.material.specific_name}: {comp.dosage_kg_m3} kg/m³ (is_cementitious: {comp.is_cementitious})")
        
    except ConcreteMix.DoesNotExist:
        print("Mix 8110 not found in database")

if __name__ == "__main__":
    main()
