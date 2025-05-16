#!/usr/bin/env python
"""
Set up a staging environment for the database refresh.

This script:
1. Creates a staging database by copying the schema from the production database
2. Sets up minimal data to test the web application functionality
"""
import os
import sys
import django
import subprocess
import argparse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django settings
from django.conf import settings

def create_staging_database():
    """Create a staging database with the same schema as the production database."""
    # Get database connection details from Django settings
    db_settings = settings.DATABASES['default']
    
    # Define staging database name
    staging_db_name = f"{db_settings['NAME']}_staging"
    
    # Set PostgreSQL environment variables
    pg_env = os.environ.copy()
    pg_env['PGPASSWORD'] = db_settings['PASSWORD']
    
    try:
        print(f"Creating staging database '{staging_db_name}'...")
        
        # Check if the staging database already exists
        check_cmd = [
            'psql',
            '-h', db_settings['HOST'],
            '-p', db_settings['PORT'],
            '-U', db_settings['USER'],
            '-c', f"SELECT 1 FROM pg_database WHERE datname = '{staging_db_name}';"
        ]
        
        process = subprocess.Popen(check_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if "1 row" in stdout.decode():
            print(f"Staging database '{staging_db_name}' already exists.")
            drop = input(f"Do you want to drop and recreate '{staging_db_name}'? (yes/no): ")
            if drop.lower() in ['yes', 'y']:
                drop_cmd = [
                    'psql',
                    '-h', db_settings['HOST'],
                    '-p', db_settings['PORT'],
                    '-U', db_settings['USER'],
                    '-c', f"DROP DATABASE {staging_db_name};"
                ]
                subprocess.run(drop_cmd, env=pg_env, check=True)
                print(f"Dropped existing staging database '{staging_db_name}'.")
            else:
                print("Using existing staging database.")
                return staging_db_name
        
        # Create the staging database
        create_cmd = [
            'psql',
            '-h', db_settings['HOST'],
            '-p', db_settings['PORT'],
            '-U', db_settings['USER'],
            '-c', f"CREATE DATABASE {staging_db_name};"
        ]
        subprocess.run(create_cmd, env=pg_env, check=True)
        print(f"Created staging database '{staging_db_name}'.")
        
        # Copy schema from production database
        print("Copying schema from production database...")
        schema_dump_cmd = [
            'pg_dump',
            '-h', db_settings['HOST'],
            '-p', db_settings['PORT'],
            '-U', db_settings['USER'],
            '-s',  # Schema-only
            db_settings['NAME']
        ]
        
        schema_restore_cmd = [
            'psql',
            '-h', db_settings['HOST'],
            '-p', db_settings['PORT'],
            '-U', db_settings['USER'],
            '-d', staging_db_name
        ]
        
        dump_process = subprocess.Popen(schema_dump_cmd, env=pg_env, stdout=subprocess.PIPE)
        restore_process = subprocess.Popen(schema_restore_cmd, env=pg_env, stdin=dump_process.stdout)
        dump_process.stdout.close()  # Allow dump_process to receive a SIGPIPE if restore_process exits
        restore_process.communicate()
        
        if restore_process.returncode != 0:
            print("Error copying schema to staging database.")
            return None
            
        print(f"Schema successfully copied to '{staging_db_name}'.")
        return staging_db_name
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating staging database: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def update_settings_for_staging(staging_db_name):
    """Create a copy of settings.py for the staging environment."""
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                'concrete_mix_project', 'settings.py')
    staging_settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        'concrete_mix_project', 'settings_staging.py')
    
    try:
        with open(settings_path, 'r') as f:
            settings_content = f.read()
        
        # Replace database name
        settings_content = settings_content.replace(
            f"'NAME': '{settings.DATABASES['default']['NAME']}'",
            f"'NAME': '{staging_db_name}'"
        )
        
        with open(staging_settings_path, 'w') as f:
            f.write(settings_content)
        
        print(f"Created staging settings at {staging_settings_path}")
        print("To use the staging database, run Django with:")
        print(f"    export DJANGO_SETTINGS_MODULE=concrete_mix_project.settings_staging")
        print("    python manage.py command")
        return True
    except Exception as e:
        print(f"Error creating staging settings: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Set up a staging environment for database refresh')
    parser.add_argument('--skip-confirm', action='store_true', 
                        help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    if not args.skip_confirm:
        print("\nThis will create a staging database for testing the database refresh.")
        confirm = input("Do you want to continue? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return
    
    # Create the staging database
    staging_db_name = create_staging_database()
    if not staging_db_name:
        print("Failed to create staging database.")
        return
    
    # Create staging settings
    update_settings_for_staging(staging_db_name)
    
    print("\nStaging environment setup complete.")
    print("Next steps:")
    print("1. Run the web application with the staging settings to verify it works")
    print("2. Test the clear_database.py script on the staging database")
    print("3. Begin implementing the refresh plan phases in the staging environment")

if __name__ == "__main__":
    main()
