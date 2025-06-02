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

if __name__ == '__main__':
    confirm = input("WARNING: This will delete all data from the application tables. Are you sure? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("Database reset cancelled.")
