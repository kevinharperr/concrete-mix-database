# Script to check material name lengths in the database

import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections

# Query to get distinct material name lengths over 20 characters
with connections['cdb'].cursor() as cursor:
    # Check longest material names
    cursor.execute(
        """SELECT subtype_code, length(subtype_code) as name_length 
           FROM material 
           WHERE length(subtype_code) > 20 
           ORDER BY name_length DESC 
           LIMIT 10"""
    )
    results = cursor.fetchall()
    
    print("\nLongest Material Names:")
    for subtype_code, length in results:
        print(f"  {subtype_code} - {length} characters")
    
    # Check material name length distribution
    cursor.execute(
        """SELECT length(subtype_code) as len, COUNT(*) as count 
           FROM material 
           GROUP BY len 
           ORDER BY len DESC"""
    )
    results = cursor.fetchall()
    
    print("\nMaterial Name Length Distribution:")
    for length, count in results:
        print(f"  {length} characters: {count} materials")
