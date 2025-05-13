# list_tables.py
# Script to list tables in the CDB database

import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections

def list_tables():
    print("\nList of tables in CDB database:\n")
    with connections['cdb'].cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        for i, (table_name,) in enumerate(tables):
            print(f"{i+1:3d}. {table_name}")

if __name__ == "__main__":
    list_tables()
