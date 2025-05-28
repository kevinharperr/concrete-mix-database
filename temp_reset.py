import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from django.db import connection
from django.apps import apps

def reset_database():
    """Reset the database by truncating all tables except Django system tables."""
    print("Starting database reset process...")
    
    # Get a cursor
    cursor = connection.cursor()
    
    # Get all models from our apps to reset
    app_models = []
    for app_config in apps.get_app_configs():
        if app_config.name in ['cdb_app', 'refresh_status']:
            app_models.extend(app_config.get_models())
    
    # Store Django auth and admin related tables we want to preserve
    preserve_tables = [
        'auth_user',
        'auth_group',
        'django_session',
        'django_admin_log',
        'django_content_type',
        'django_migrations'
    ]
    
    # Temporarily disable foreign key constraints
    cursor.execute('SET CONSTRAINTS ALL DEFERRED;')
    
    # Truncate each model table
    tables_truncated = 0
    for model in app_models:
        table_name = model._meta.db_table
        if table_name not in preserve_tables:
            print(f"Truncating table: {table_name}")
            try:
                cursor.execute(f'TRUNCATE TABLE "{table_name}" CASCADE;')
                tables_truncated += 1
            except Exception as e:
                print(f"Error truncating {table_name}: {e}")
    
    # Re-enable constraints
    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE;')
    
    print(f"Database reset complete. {tables_truncated} tables were truncated.")
    print("The system is now ready for data import.")

# Directly call the reset function without confirmation
reset_database()

# Now let's reset all sequences to ensure proper ID assignment
def reset_sequences():
    """Reset all sequences in the database to ensure proper ID assignment."""
    print("\nResetting database sequences...")
    cursor = connection.cursor()
    
    # Get a list of all sequences in the database
    cursor.execute("""
        SELECT c.relname 
        FROM pg_class c 
        WHERE c.relkind = 'S' 
        AND c.relnamespace IN (
            SELECT n.oid 
            FROM pg_namespace n 
            WHERE n.nspname NOT LIKE 'pg_%' 
            AND n.nspname != 'information_schema'
        )
    """)
    
    sequences = cursor.fetchall()
    reset_count = 0
    
    for seq in sequences:
        seq_name = seq[0]
        try:
            # Reset the sequence to 1
            cursor.execute(f'ALTER SEQUENCE {seq_name} RESTART WITH 1;')
            print(f"Reset sequence: {seq_name}")
            reset_count += 1
        except Exception as e:
            print(f"Error resetting sequence {seq_name}: {e}")
    
    print(f"\nSequence reset complete. {reset_count} sequences were reset.")

# Reset the sequences
reset_sequences()

# Verify tables are empty
def verify_empty_tables():
    """Verify that all tables are properly emptied."""
    print("\nVerifying empty tables...")
    
    cursor = connection.cursor()
    
    # Get all models from our apps
    all_empty = True
    non_empty_tables = []
    
    for app_config in apps.get_app_configs():
        if app_config.name in ['cdb_app', 'refresh_status']:
            for model in app_config.get_models():
                table_name = model._meta.db_table
                if table_name not in ['auth_user', 'auth_group', 'django_session', 'django_admin_log', 'django_content_type', 'django_migrations']:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    count = cursor.fetchone()[0]
                    if count > 0:
                        all_empty = False
                        non_empty_tables.append((table_name, count))
    
    if all_empty:
        print("All tables are empty and ready for import.")
    else:
        print("WARNING: The following tables still contain data:")
        for table, count in non_empty_tables:
            print(f"  - {table}: {count} rows")

# Verify that tables are empty
verify_empty_tables()
