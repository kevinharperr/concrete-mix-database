# Script to check material names and lengths
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections

with connections['cdb'].cursor() as cursor:
    # First check the table structure
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'material'")
    columns = [row[0] for row in cursor.fetchall()]
    print("\nMaterial table columns:", ", ".join(columns))
    
    # Get the 10 longest material names
    cursor.execute("""
        SELECT m.material_id, m.material_class_id, m.subtype_code, LENGTH(m.subtype_code) as name_length
        FROM material m
        WHERE m.subtype_code IS NOT NULL
        ORDER BY name_length DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    
    print("\n10 Longest Material Names in Database:")
    print("-" * 70)
    print(f"{'ID':<6} {'Class':<10} {'Length':<8} {'Name':<45}")
    print("-" * 70)
    
    if results:
        for row in results:
            material_id, class_id, subtype_code, length = row
            print(f"{material_id:<6} {class_id:<10} {length:<8} {subtype_code}")
    else:
        print("No results found")
