# Script to check the results of DS6 data import
import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, Material, MixComponent, Dataset, MaterialProperty, AggregateDetail
from django.db import transaction

def check_ds6_data():
    print("\nChecking DS6 data in database:")
    
    # Check for DS6 dataset
    try:
        ds6_dataset = Dataset.objects.using("cdb").get(dataset_name="DS6")
        print(f"Found DS6 dataset: {ds6_dataset.dataset_name}")
    except Dataset.DoesNotExist:
        print("DS6 dataset not found in database!")
        return
    
    # Count DS6 mixes with proper prefix
    ds6_mixes = ConcreteMix.objects.using("cdb").filter(mix_code__startswith="DS6-")
    print(f"DS6 mixes with proper prefix: {len(ds6_mixes)}")
    
    # Count all mixes with DS6 dataset
    all_ds6_mixes = ConcreteMix.objects.using("cdb").filter(dataset=ds6_dataset)
    print(f"Total DS6 mixes (by dataset): {len(all_ds6_mixes)}")
    
    # Check if there's any discrepancy
    if len(ds6_mixes) != len(all_ds6_mixes):
        print(f"WARNING: {len(all_ds6_mixes) - len(ds6_mixes)} DS6 mixes don't have the proper DS6- prefix!")
        
        # Show examples of mixes without proper prefix
        bad_prefix_mixes = all_ds6_mixes.exclude(mix_code__startswith="DS6-")[:5]
        if bad_prefix_mixes.exists():
            print("Examples of bad prefix mixes:")
            for mix in bad_prefix_mixes:
                print(f"  Mix ID: {mix.pk}, Mix Code: {mix.mix_code}")
    
    # Check components
    if len(ds6_mixes) > 0:
        # Pick a sample mix to check
        sample_mix = ds6_mixes.first()
        components = MixComponent.objects.using("cdb").filter(mix=sample_mix)
        print(f"\nSample mix {sample_mix.mix_code} has {len(components)} components:")
        
        for comp in components:
            print(f"  - {comp.material.specific_name}: {comp.dosage_kg_m3} kg/m³")
        
        # Check for NCA and RCA
        for material_type in ["NCA", "RCA", "NFA"]:
            matching_materials = Material.objects.using("cdb").filter(subtype_code=material_type)
            print(f"\nFound {len(matching_materials)} materials with subtype {material_type}")
            
            if matching_materials.exists():
                # Check aggregate details
                for material in matching_materials[:2]:  # Check first two
                    try:
                        details = AggregateDetail.objects.using("cdb").filter(material=material)
                        if details.exists():
                            detail = details.first()
                            print(f"  Found aggregate detail for {material.specific_name}:")
                            # List all fields and values
                            for field in detail._meta.get_fields():
                                if not field.is_relation:
                                    value = getattr(detail, field.name, None)
                                    print(f"    {field.name}: {value}")
                        else:
                            print(f"  No aggregate details for {material.specific_name}")
                    except Exception as e:
                        print(f"  Error checking aggregate details: {e}")
                    
                    # Check material properties
                    try:
                        properties = MaterialProperty.objects.using("cdb").filter(material=material)
                        if properties.exists():
                            print(f"  Found {len(properties)} properties for {material.specific_name}:")
                            for prop in properties[:3]:  # Show first three
                                print(f"    {prop.property_name.property_name}: {prop.value_num}")
                        else:
                            print(f"  No properties for {material.specific_name}")
                    except Exception as e:
                        print(f"  Error checking material properties: {e}")
    
    # Check for total errors in the import
    print("\nAnalyzing AggregateDetail model:")
    try:
        aggregate_fields = [f.name for f in AggregateDetail._meta.get_fields() if not f.is_relation]
        print(f"Available fields in AggregateDetail model: {aggregate_fields}")
    except Exception as e:
        print(f"Error analyzing AggregateDetail model: {e}")

if __name__ == "__main__":
    print("\nRunning DS6 Data Check")
    check_ds6_data()
    print("\nDone!")
