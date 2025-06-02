# Script to directly check DB values and components

import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix, MixComponent, PerformanceResult
from django.db import connection

# Check directly with SQL to bypass any Django ORM caching
def check_with_raw_sql():
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT mix_id, mix_code, w_b_ratio, w_c_ratio 
               FROM concrete_mix 
               WHERE mix_id IN (225, 5630, 917, 13562, 5596, 911, 13561, 987, 13560)""")
        results = cursor.fetchall()
        
        print("\nDirect SQL query results:")
        for row in results:
            print(f"Mix ID: {row[0]}, Mix Code: {row[1]}, w/b ratio: {row[2]}, w/c ratio: {row[3]}")

# Create a dataframe similar to how the notebook does it
def check_dataframe_loading():
    mixes = ConcreteMix.objects.filter(pk__in=[225, 5630, 917, 13562, 5596, 911, 13561, 987, 13560])
    
    # This mimics the dataframe creation in the notebook
    data = []
    for mix in mixes:
        record = {
            'mix_id': mix.mix_id,
            'mix_code': mix.mix_code,
            'w_b_ratio': mix.w_b_ratio,
            'w_c_ratio': mix.w_c_ratio
        }
        data.append(record)
    
    df = pd.DataFrame(data)
    print("\nDataFrame created from Django ORM:")
    print(df)

# Check database connection state
def check_db_connection():
    print("\nDatabase connection info:")
    print(f"Connection: {connection}")
    print(f"Connection settings: {connection.settings_dict['NAME']}")
    print(f"Is usable: {connection.is_usable()}")

# Run all checks
print("\n=== DIRECT DATABASE CHECKS ===\n")
check_with_raw_sql()
check_dataframe_loading()
check_db_connection()
