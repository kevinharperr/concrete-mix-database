#!/usr/bin/env python
"""
Reset sequences for all tables in the database.
This is particularly useful after clearing data or direct SQL operations.
"""
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
django.setup()

# Import Django models
from django.db import connection

def reset_all_sequences():
    """Reset all sequences in the database to their next valid values."""
    with connection.cursor() as cursor:
        # Get all table names in the current schema
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(tables)} tables")
        
        # For each table, try to reset its primary key sequence
        for table in tables:
            try:
                # Get primary key column for the table
                cursor.execute(f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = '{table}'::regclass
                    AND i.indisprimary;
                """)
                pk_column = cursor.fetchone()
                
                if pk_column:
                    pk_column = pk_column[0]
                    # Reset sequence based on max value in the table
                    cursor.execute(f"""
                        SELECT setval(pg_get_serial_sequence('{table}', '{pk_column}'), 
                                     COALESCE((SELECT MAX({pk_column}) FROM {table}), 0) + 1, false);
                    """)
                    print(f"Reset sequence for {table}.{pk_column}")
            except Exception as e:
                print(f"Error resetting sequence for {table}: {str(e)}")
        
        print("\nSequence reset complete")

if __name__ == "__main__":
    print("Resetting all sequences in the database...")
    reset_all_sequences()
