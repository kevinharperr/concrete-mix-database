# Script to check material name lengths in the database
import os
import sys
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

# Import models after setting up Django
from cdb_app.models import Material

# Query material records with long names
long_materials = Material.objects.using('cdb').raw(
    "SELECT * FROM material WHERE length(subtype_code) > 20 ORDER BY length(subtype_code) DESC LIMIT 10"
)

print("\nLongest Material Names:")
for material in long_materials:
    print(f"  {material.subtype_code} - {len(material.subtype_code)} characters")

# Check if any material names are using the full 60 character length
max_length_materials = Material.objects.using('cdb').raw(
    "SELECT * FROM material WHERE length(subtype_code) > 50 ORDER BY length(subtype_code) DESC LIMIT 5"
)

max_length_count = sum(1 for _ in max_length_materials)
if max_length_count > 0:
    print("\nMaterials approaching max length (50+ characters):")
    for material in Material.objects.using('cdb').raw(
            "SELECT * FROM material WHERE length(subtype_code) > 50 ORDER BY length(subtype_code) DESC LIMIT 5"):
        print(f"  {material.subtype_code} - {len(material.subtype_code)} characters")
else:
    print("\nNo materials approaching the 60 character limit found.")
