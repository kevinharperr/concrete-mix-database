#!/usr/bin/env python
"""
Diagnostic script to check water-binder ratio calculations.
This script helps verify correct cementitious material identification
and water-binder ratio calculations.
"""

import os
import sys
import django
import pandas as pd
from decimal import Decimal

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Now import Django models
from cdb_app.models import ConcreteMix, MixComponent, Material
from django.db.models import Sum, F

def check_cementitious_materials():
    """Check and display all materials flagged as cementitious."""
    print("\n=== CEMENTITIOUS MATERIALS ===")
    
    # Get all unique materials that are used in any mix component
    all_materials = Material.objects.filter(
        mix_usages__is_cementitious=True
    ).distinct()
    
    print(f"Found {all_materials.count()} cementitious materials")
    
    # Display information about each cementitious material
    print(f"{'Material ID':<12} {'Material Class':<15} {'Subtype':<15} {'Name':<30}")
    print("-" * 72)
    
    for material in all_materials:
        material_class = material.material_class.class_code if material.material_class else "None"
        print(f"{material.material_id:<12} {material_class:<15} {material.subtype_code or 'None':<15} {material.specific_name or 'None':<30}")
    
    return all_materials.count()

def check_high_wb_ratios(threshold=0.8):
    """Find and display mixes with high w/b ratios."""
    print(f"\n=== MIXES WITH HIGH W/B RATIOS (>{threshold}) ===")
    
    high_wb_mixes = ConcreteMix.objects.filter(w_b_ratio__gt=threshold)
    
    print(f"Found {high_wb_mixes.count()} mixes with w/b ratio > {threshold}")
    
    if high_wb_mixes:
        print(f"{'Mix ID':<10} {'Mix Code':<20} {'W/B Ratio':<10} {'W/C Ratio':<10}")
        print("-" * 50)
        
        for mix in high_wb_mixes:
            print(f"{mix.mix_id:<10} {mix.mix_code or 'None':<20} {mix.w_b_ratio or 'None':<10} {mix.w_c_ratio or 'None':<10}")
    
    return high_wb_mixes.count()

def analyze_mix_detail(mix_id):
    """Analyze composition details for a specific mix."""
    try:
        mix = ConcreteMix.objects.get(mix_id=mix_id)
    except ConcreteMix.DoesNotExist:
        print(f"Mix ID {mix_id} not found")
        return None
    
    print(f"\n=== DETAILED ANALYSIS OF MIX {mix_id} ===")
    print(f"Mix Code: {mix.mix_code}")
    print(f"Stored W/B Ratio: {mix.w_b_ratio}")
    print(f"Stored W/C Ratio: {mix.w_c_ratio}")
    print(f"Stored WB-K Reported: {mix.wb_k_reported}")
    
    # Get components
    components = MixComponent.objects.filter(mix=mix).select_related('material', 'material__material_class')
    
    # Calculate key totals
    water_content = components.filter(material__material_class__class_code='WATER').aggregate(
        total=Sum('dosage_kg_m3'))['total'] or Decimal('0')
    
    cement_content = components.filter(material__material_class__class_code='CEMENT').aggregate(
        total=Sum('dosage_kg_m3'))['total'] or Decimal('0')
    
    scm_content = components.filter(material__material_class__class_code='SCM').aggregate(
        total=Sum('dosage_kg_m3'))['total'] or Decimal('0')
    
    cementitious_content = components.filter(is_cementitious=True).aggregate(
        total=Sum('dosage_kg_m3'))['total'] or Decimal('0')
    
    # Calculate ratios
    simple_wb = water_content / cementitious_content if cementitious_content else None
    wc = water_content / cement_content if cement_content else None
    
    print(f"\nCalculated values:")
    print(f"Water content: {water_content:.2f} kg/m³")
    print(f"Cement content: {cement_content:.2f} kg/m³")
    print(f"SCM content: {scm_content:.2f} kg/m³")
    print(f"Total cementitious content: {cementitious_content:.2f} kg/m³")
    print(f"Simple W/B ratio (water/cementitious): {simple_wb:.3f}" if simple_wb else "Simple W/B ratio: N/A")
    print(f"W/C ratio (water/cement): {wc:.3f}" if wc else "W/C ratio: N/A")
    
    print("\nComponent breakdown:")
    print(f"{'Material ID':<12} {'Class':<10} {'Subtype':<10} {'Dosage (kg/m³)':<16} {'Cementitious?':<12} {'Name':<20}")
    print("-" * 80)
    
    for comp in components:
        material = comp.material
        material_class = material.material_class.class_code if material.material_class else "None"
        print(f"{material.material_id:<12} {material_class:<10} {material.subtype_code or 'None':<10} "
              f"{comp.dosage_kg_m3:<16.2f} {'Yes' if comp.is_cementitious else 'No':<12} "
              f"{material.specific_name or 'None':<20}")
    
    return {
        'mix_id': mix_id,
        'w_b_ratio': mix.w_b_ratio,
        'calculated_wb': simple_wb,
        'w_c_ratio': mix.w_c_ratio,
        'calculated_wc': wc,
        'water_content': water_content,
        'cement_content': cement_content,
        'scm_content': scm_content,
        'cementitious_content': cementitious_content
    }

def main():
    print("Water-Binder Ratio Diagnostic Tool")
    print("=" * 40)
    
    # Check command line arguments for specific mix IDs
    import sys
    specific_mix_ids = []
    if len(sys.argv) > 1:
        try:
            specific_mix_ids = [int(arg) for arg in sys.argv[1:]]
            print(f"Analyzing specific mix IDs: {specific_mix_ids}")
        except ValueError:
            print("Invalid mix ID. Please provide numeric mix IDs.")
    
    # Check cementitious materials
    cementitious_count = check_cementitious_materials()
    
    # Check high w/b ratios
    high_wb_count = check_high_wb_ratios(threshold=0.7)  # Changed from 0.8 to 0.7 to match user's concern
    
    # Analyze specific mixes
    print("\n=== ANALYZING SPECIFIC MIXES ===")
    results = []
    
    # If specific mix IDs were provided, check only those
    mix_ids_to_check = specific_mix_ids if specific_mix_ids else [8110, 633, 634, 4884, 612, 614, 613, 611, 616, 632, 615, 4893, 635, 636]
    
    for mix_id in mix_ids_to_check:
        result = analyze_mix_detail(mix_id)
        if result:
            results.append(result)
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"Total cementitious materials identified: {cementitious_count}")
    print(f"Total mixes with high w/b ratio (>0.7): {high_wb_count}")
    
    if results:
        print("\nChecked mix summary:")
        for r in results:
            diff = abs(r['w_b_ratio'] - r['calculated_wb']) if r['w_b_ratio'] and r['calculated_wb'] else None
            print(f"Mix {r['mix_id']}: Stored W/B={r['w_b_ratio']}, Calculated W/B={r['calculated_wb']:.3f}" +
                  (f" (diff: {diff:.3f})" if diff else ""))

if __name__ == "__main__":
    main()
