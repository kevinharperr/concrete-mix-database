# Script to fix material binding issues for DS6 import
import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, Material, MixComponent, MaterialProperty, PropertyDictionary, AggregateDetail
from django.db import transaction

# Constants
DATASET_NAME = "DS6"
MIX_PREFIX = "DS6-"

@transaction.atomic
def fix_material_binding():
    print(f"Fixing material binding for {DATASET_NAME} dataset")
    
    # Get all mixes with the DS6 prefix
    ds6_mixes = ConcreteMix.objects.using("cdb").filter(mix_code__startswith=MIX_PREFIX)
    print(f"Found {len(ds6_mixes)} mixes with prefix {MIX_PREFIX}")
    
    # Process each mix
    for mix in ds6_mixes:
        print(f"\nProcessing mix: {mix.mix_code}")
        
        # 1. Identify all materials in this mix
        components = MixComponent.objects.using("cdb").filter(mix=mix)
        print(f"  Found {len(components)} components")
        
        # Create a dictionary to store materials by type
        materials_by_type = {}
        
        # Categorize materials by their class and subtype
        for comp in components:
            material = comp.material
            # Create standardized keys for common material types
            if material.material_class_id == "AGGR_C" and material.subtype_code == "NCA":
                materials_by_type["NCA"] = material
            elif material.material_class_id == "AGGR_C" and material.subtype_code == "RCA":
                materials_by_type["RCA"] = material
            elif material.material_class_id == "AGGR_F" and material.subtype_code == "NFA":
                materials_by_type["NFA"] = material
            # Add more categories as needed
        
        # 2. Fix aggregate details - link to appropriate materials
        for agg_type in ["NCA", "RCA", "NFA"]:
            if agg_type in materials_by_type:
                material = materials_by_type[agg_type]
                print(f"  Checking {agg_type} properties for material {material.material_id}")
                
                # Get or create aggregate detail for this material
                agg_detail, created = AggregateDetail.objects.using("cdb").get_or_create(
                    material=material,
                    defaults={
                        "specific_gravity": None,
                        "d_lower_mm": None,
                        "d_upper_mm": None,
                        "fineness_modulus": None,
                        "water_absorption_pct": None,
                        "unit_weight_kg_m3": None
                    }
                )
                
                if created:
                    print(f"    Created new aggregate details for {agg_type}")
                else:
                    print(f"    Found existing aggregate details for {agg_type}")
        
        # 3. Fix material properties - ensure they're linked to proper materials
        for agg_type in ["NCA", "RCA", "NFA"]:
            if agg_type in materials_by_type:
                material = materials_by_type[agg_type]
                
                # Check property dictionary entries exist
                for prop_name in ["la_abrasion_pct", "crushing_index_pct"]:
                    prop_dict, created = PropertyDictionary.objects.using("cdb").get_or_create(
                        property_name=prop_name,
                        defaults={
                            "display_name": prop_name.replace("_", " ").title(),
                            "property_group": "physical"
                        }
                    )
                    
                    # Check if property exists for this material
                    prop_exists = MaterialProperty.objects.using("cdb").filter(
                        material=material,
                        property_name=prop_dict
                    ).exists()
                    
                    if not prop_exists:
                        print(f"    Property {prop_name} missing for {agg_type}, would be created with values from dataset")

def perform_health_check():
    print("\nPerforming health check for DS6 dataset")
    
    # Count DS6 mixes
    ds6_mixes = ConcreteMix.objects.using("cdb").filter(mix_code__startswith=MIX_PREFIX)
    print(f"Total DS6 mixes: {len(ds6_mixes)}")
    
    # Count components in DS6 mixes
    total_components = 0
    materials_seen = set()
    
    for mix in ds6_mixes:
        components = MixComponent.objects.using("cdb").filter(mix=mix)
        total_components += len(components)
        
        # Collect unique materials
        for comp in components:
            materials_seen.add(comp.material.material_id)
    
    print(f"Total components across all mixes: {total_components}")
    print(f"Unique materials used: {len(materials_seen)}")
    
    # Check aggregate details
    aggregates = AggregateDetail.objects.using("cdb").filter(material__material_id__in=materials_seen)
    print(f"Aggregate details entries: {len(aggregates)}")
    
    # Check material properties
    properties = MaterialProperty.objects.using("cdb").filter(material__material_id__in=materials_seen)
    print(f"Material property entries: {len(properties)}")

if __name__ == "__main__":
    print("Running Material Binding Fix for DS6 Dataset")
    fix_material_binding()
    perform_health_check()
    print("Done!")
