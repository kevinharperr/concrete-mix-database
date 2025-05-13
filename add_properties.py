# Script to add missing property dictionary entries for DS6 import
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app.models import PropertyDictionary, UnitLookup

# Properties to add
properties_to_add = [
    # Main moduli properties
    {"property_name": "reactivity_modulus", "display_name": "Reactivity Modulus", "property_group": "chemical"},
    {"property_name": "silica_modulus", "display_name": "Silica Modulus", "property_group": "chemical"},
    {"property_name": "alumina_modulus", "display_name": "Alumina Modulus", "property_group": "chemical"},
    
    # Other required properties
    {"property_name": "tio2_pct", "display_name": "TiO2 (%)", "property_group": "chemical"},
    {"property_name": "p2o5_pct", "display_name": "P2O5 (%)", "property_group": "chemical"},
    {"property_name": "sro_pct", "display_name": "SrO (%)", "property_group": "chemical"},
    {"property_name": "mn2o3_pct", "display_name": "Mn2O3 (%)", "property_group": "chemical"},
    {"property_name": "median_particle_size_mm", "display_name": "D50 Median Particle Size (mm)", "property_group": "physical"},
]

# Get percentage unit (for chemical compositions)
unit_pct, _ = UnitLookup.objects.using('cdb').get_or_create(
    unit_symbol="%",
    defaults={
        "description": "Percentage",
        "si_factor": 0.01
    }
)

# Add properties if they don't exist
print("Adding missing properties to PropertyDictionary:")
for prop in properties_to_add:
    obj, created = PropertyDictionary.objects.using('cdb').get_or_create(
        property_name=prop["property_name"],
        defaults={
            "display_name": prop["display_name"],
            "property_group": prop["property_group"],
            # Set default unit for percentage properties
            "default_unit": unit_pct if prop["property_name"].endswith("_pct") else None
        }
    )
    
    status = "Created" if created else "Already exists"
    print(f"  {status}: {prop['property_name']} - {prop['display_name']}")

print("\nAll required properties have been added.")
