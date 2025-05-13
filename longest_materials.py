# Script to check the 10 longest material names
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections

with connections['cdb'].cursor() as cursor:
    # Get the 10 longest material names using the correct column names
    cursor.execute("""
        SELECT m.material_id, m.class_code, m.subtype_code, LENGTH(m.subtype_code) as name_length
        FROM material m
        WHERE m.subtype_code IS NOT NULL
        ORDER BY name_length DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    
    print("\n10 Longest Material Names in Database:")
    print("-" * 75)
    print(f"{'ID':<6} {'Class':<10} {'Length':<8} {'Name':<50}")
    print("-" * 75)
    
    if results:
        for row in results:
            material_id, class_code, subtype_code, length = row
            print(f"{material_id:<6} {class_code:<10} {length:<8} {subtype_code}")
    else:
        print("No results found")
