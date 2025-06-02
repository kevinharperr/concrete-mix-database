#!/usr/bin/env python
"""
Set up a testing environment for Phase 3 of the Database Refresh Plan.

This script:
1. Creates a clean staging database structure
2. Sets up minimal required data for testing the ETL process
3. Enables read-only mode for testing the database protection
"""
import os
import sys
import django
import subprocess
import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
django.setup()

from django.db import connection
from refresh_status.models import DatabaseStatus, RefreshLogEntry, StatusNotification
from cdb_app.models import Dataset, MaterialClass, UnitLookup

def reset_staging_database():
    """Clear and reset the staging database."""
    print(f"\nStarting Phase 3: Test Migration setup at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Drop all tables in the staging database
    with connection.cursor() as cursor:
        # Disable foreign key constraints temporarily
        print("Disabling foreign key constraints...")
        cursor.execute("SET session_replication_role = 'replica';")
        
        # Get a list of all tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname='public' AND 
            tablename != 'django_migrations' AND
            tablename != 'sqlite_sequence'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Drop each table
        for table in tables:
            print(f"Dropping table: {table}")
            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        
        # Re-enable foreign key constraints
        cursor.execute("SET session_replication_role = 'origin';")
    
    # Run migrations to create a fresh schema
    print("\nCreating fresh database schema...")
    subprocess.run(['python', 'manage.py', 'migrate'], check=True)
    
    print("\nStaging database has been reset with a clean schema.")
    return True

def create_test_data():
    """Create minimal test data for testing the ETL process."""
    print("\nCreating test data for migration testing...")
    
    # Create essential material classes
    material_classes = [
        {'class_code': 'CEMENT', 'class_name': 'Cement'},
        {'class_code': 'SCM', 'class_name': 'Supplementary Cementitious Material'},
        {'class_code': 'AGGR_C', 'class_name': 'Coarse Aggregate'},
        {'class_code': 'AGGR_F', 'class_name': 'Fine Aggregate'},
        {'class_code': 'WATER', 'class_name': 'Water'},
        {'class_code': 'ADMIX', 'class_name': 'Admixture'},
        {'class_code': 'FIBER', 'class_name': 'Fiber'}
    ]
    
    for mc in material_classes:
        MaterialClass.objects.get_or_create(
            class_code=mc['class_code'],
            defaults={'class_name': mc['class_name']}
        )
    print("Created essential material classes.")
    
    # Create essential units
    units = [
        {'unit_symbol': 'kg/m³', 'description': 'Kilograms per cubic meter'},
        {'unit_symbol': 'MPa', 'description': 'Megapascals'},
        {'unit_symbol': '%', 'description': 'Percent'}
    ]
    
    for unit in units:
        UnitLookup.objects.get_or_create(
            unit_symbol=unit['unit_symbol'],
            defaults={'description': unit['description']}
        )
    print("Created essential unit lookups.")
    
    # Create test dataset
    Dataset.objects.get_or_create(
        dataset_name='DS0',
        defaults={'license': 'Test dataset for ETL validation'}
    )
    print("Created test dataset.")
    
    # Create a second dataset for reference
    Dataset.objects.get_or_create(
        dataset_name='DS_TEST',
        defaults={'license': 'Validation dataset for ETL testing'}
    )
    print("Created validation dataset.")
    
    return True

def setup_refresh_status():
    """Set up the database refresh status for testing."""
    print("\nSetting up refresh status and notifications...")
    
    # Create initial database status
    status = DatabaseStatus.objects.create(
        status=DatabaseStatus.IN_PROGRESS,
        read_only_mode=DatabaseStatus.READ_ONLY_ON,
        current_phase="Phase 3: Test Migration",
        current_step="1. Staging Database Reset",
        progress_percentage=10,
        maintenance_message="Database refresh testing in progress. The database is currently in read-only mode."
    )
    print("Created database status entry.")
    
    # Create test log entries
    RefreshLogEntry.objects.create(
        phase="Phase 3: Test Migration",
        step="1. Staging Database Reset",
        status="info",
        message="Staging database reset completed successfully",
        is_error=False,
        details={
            "tables_created": "all required tables",
            "test_data": "minimal test data for ETL testing"
        }
    )
    print("Created test log entry.")
    
    # Create notification
    StatusNotification.objects.create(
        title="Database Refresh Testing",
        message="We are currently testing the database refresh process. The application is in read-only mode.",
        notification_type=StatusNotification.INFO,
        is_active=True,
        display_until=datetime.datetime.now() + datetime.timedelta(days=7),
        display_on="all"
    )
    print("Created test notification.")
    
    return True

def main():
    try:
        # Reset the database
        if not reset_staging_database():
            print("Failed to reset staging database.")
            return False
        
        # Create test data
        if not create_test_data():
            print("Failed to create test data.")
            return False
        
        # Set up refresh status
        if not setup_refresh_status():
            print("Failed to set up refresh status.")
            return False
        
        print("\nPhase 3: Test Migration environment has been set up successfully!")
        print("The staging database has been prepared and is now in read-only mode.")
        print("You can now proceed with testing the ETL process.")
        return True
        
    except Exception as e:
        print(f"Error setting up test environment: {str(e)}")
        return False

if __name__ == "__main__":
    main()
