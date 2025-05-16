#!/usr/bin/env python
"""
Database export utility for the Concrete Mix Database.

This script creates a complete database dump that can be easily shared
and restored by colleagues. It also creates a README with instructions.
"""
import os
import sys
import django
import subprocess
import datetime
import shutil

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django settings
from django.conf import settings

def create_database_dump():
    """Create a complete PostgreSQL database dump."""
    # Get database connection details from Django settings
    db_settings = settings.DATABASES['default']
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_export')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate timestamp for the export
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Define export filenames
    sql_filename = f"cdb_database_dump_{timestamp}.sql"
    sql_filepath = os.path.join(output_dir, sql_filename)
    
    # Build the pg_dump command
    pg_dump_cmd = [
        'pg_dump',
        '-h', db_settings['HOST'],
        '-p', db_settings['PORT'],
        '-U', db_settings['USER'],
        '-F', 'c',  # Custom/compressed format
        '-b',  # Include large objects
        '-v',  # Verbose mode
        '-f', sql_filepath.replace('.sql', '.backup'),
        db_settings['NAME']
    ]
    
    # Also create plain SQL for easier viewing if needed
    pg_dump_sql_cmd = [
        'pg_dump',
        '-h', db_settings['HOST'],
        '-p', db_settings['PORT'],
        '-U', db_settings['USER'],
        '--schema=public',
        '-f', sql_filepath,
        db_settings['NAME']
    ]
    
    try:
        # Set PGPASSWORD environment variable for authentication
        pg_env = os.environ.copy()
        pg_env['PGPASSWORD'] = db_settings['PASSWORD']
        
        # Execute pg_dump for binary backup
        print(f"Creating binary database dump to {sql_filepath.replace('.sql', '.backup')}...")
        process = subprocess.Popen(pg_dump_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Error creating binary database dump: {stderr.decode()}")
            return None
        
        # Execute pg_dump for SQL backup
        print(f"Creating SQL database dump to {sql_filepath}...")
        process = subprocess.Popen(pg_dump_sql_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Error creating SQL database dump: {stderr.decode()}")
            return None
        
        print(f"Database dump created successfully in {output_dir}")
        return {
            'binary_dump': sql_filepath.replace('.sql', '.backup'),
            'sql_dump': sql_filepath,
            'timestamp': timestamp,
            'db_name': db_settings['NAME']
        }
    
    except Exception as e:
        print(f"Error creating database dump: {str(e)}")
        return None

def create_readme(dump_info):
    """Create a README file with import instructions."""
    if not dump_info:
        return
    
    output_dir = os.path.dirname(dump_info['binary_dump'])
    readme_path = os.path.join(output_dir, 'README.md')
    
    readme_content = f"""# Concrete Mix Database Export

## Overview

This directory contains a database export of the Concrete Mix Database (CDB) application.

**Export Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Database Name:** {dump_info['db_name']}

## Files Included

- `{os.path.basename(dump_info['binary_dump'])}`: Binary format database dump (for direct restoration)
- `{os.path.basename(dump_info['sql_dump'])}`: SQL format database dump (for inspection or manual import)

## Import Instructions

### Prerequisites

- PostgreSQL should be installed on your system
- The CDB application code should be set up

### Option 1: Binary Restoration (Recommended)

```bash
# Create the database if it doesn't exist
psql -c 'CREATE DATABASE cdb;' -U postgres

# Restore the database from the binary dump
pg_restore -d cdb -U postgres {os.path.basename(dump_info['binary_dump'])}
```

### Option 2: SQL Import

```bash
# Create the database if it doesn't exist
psql -c 'CREATE DATABASE cdb;' -U postgres

# Import the SQL dump
psql -d cdb -U postgres -f {os.path.basename(dump_info['sql_dump'])}
```

## Application Setup

After restoring the database, make sure your Django settings are configured to connect to this database:

```python
DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cdb',
        'USER': 'postgres',
        'PASSWORD': 'your_password',  # Set your own password
        'HOST': 'localhost',
        'PORT': '5432',
    }}
}}
```

## Important Notes

* This database export contains all concrete mix data, including material properties, mix components, and test results
* Some high water-binder ratios have been identified in certain mixes (particularly in DS2 dataset), as documented in the LESSONS_LEARNED.md file
* The database structure is designed to work with the CDB web application

## Contact

For questions or issues with this database export, please contact the database administrator.
"""
    
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"Created README with import instructions at {readme_path}")
    return readme_path

def create_zip_archive(dump_info):
    """Create a ZIP archive of the database export files."""
    if not dump_info:
        return
    
    output_dir = os.path.dirname(dump_info['binary_dump'])
    zip_filename = f"concrete_mix_database_export_{dump_info['timestamp']}.zip"
    zip_filepath = os.path.join(os.path.dirname(output_dir), zip_filename)
    
    # Create ZIP archive
    shutil.make_archive(
        zip_filepath.replace('.zip', ''),
        'zip',
        output_dir
    )
    
    print(f"Created ZIP archive at {zip_filepath}")
    return zip_filepath

def add_supporting_files(output_dir):
    """Add supporting files to the export directory."""
    # Copy the lessons learned file to provide context
    lessons_file = os.path.join(os.path.dirname(output_dir), 'LESSONS_LEARNED.md')
    if os.path.exists(lessons_file):
        shutil.copy(lessons_file, output_dir)
        print(f"Added lessons learned file to the export")
    
    # Add a copy of the database schema diagram if it exists
    schema_file = os.path.join(os.path.dirname(output_dir), 'database_schema.png')
    if os.path.exists(schema_file):
        shutil.copy(schema_file, output_dir)
        print(f"Added database schema diagram to the export")

def main():
    print("\nConcrete Mix Database Export Utility\n" + "=" * 35)
    
    # Create the database dump
    dump_info = create_database_dump()
    
    if dump_info:
        # Add supporting files
        add_supporting_files(os.path.dirname(dump_info['binary_dump']))
        
        # Create README file
        create_readme(dump_info)
        
        # Create ZIP archive
        zip_file = create_zip_archive(dump_info)
        
        print("\nExport Summary:\n" + "-" * 20)
        print(f"Database: {dump_info['db_name']}")
        print(f"Export timestamp: {dump_info['timestamp']}")
        print(f"Binary dump: {os.path.basename(dump_info['binary_dump'])}")
        print(f"SQL dump: {os.path.basename(dump_info['sql_dump'])}")
        print(f"ZIP archive: {os.path.basename(zip_file) if zip_file else 'Not created'}")
        print("\nShare the ZIP archive with your colleague.")
        print("They will need to extract it and follow the instructions in the README.md file.")
    else:
        print("Failed to create database export.")

if __name__ == "__main__":
    main()
