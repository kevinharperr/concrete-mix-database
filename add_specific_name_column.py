# add_specific_name_column.py
# Script to add missing specific_name column

import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from django.db import connections

# SQL to add the specific_name column if it doesn't exist
sql = """
ALTER TABLE material ADD COLUMN IF NOT EXISTS specific_name TEXT;
"""

with connections['cdb'].cursor() as cursor:
    print("Executing SQL to add specific_name column...")
    cursor.execute(sql)
    print("Done.")
