#!/usr/bin/env python
"""
Reset and prepare the staging database for Phase 3: Test Migration.

This script:
1. Drops and recreates the staging database
2. Runs Django migrations to set up the schema
3. Creates essential lookup data for testing
4. Initializes the refresh status system
"""
import os
import sys
import django
import subprocess
import datetime
import time

def recreate_staging_database():
    """Drop and recreate the staging database."""
    print(f"\nResetting staging database at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Set PostgreSQL environment variables
    os.environ["PGPASSWORD"] = "264537"
    
    # Terminate existing connections
    print("Terminating existing connections...")
    subprocess.run([
        "psql",
        "-h", "localhost",
        "-p", "5432",
        "-U", "postgres",
        "-c", "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'cdb_staging' AND pid <> pg_backend_pid();"
    ], check=False)
    
    # Drop the database if it exists
    print("Dropping existing staging database...")
    subprocess.run([
        "psql",
        "-h", "localhost",
        "-p", "5432",
        "-U", "postgres",
        "-c", "DROP DATABASE IF EXISTS cdb_staging;"
    ], check=True)
    
    # Create a fresh database
    print("Creating fresh staging database...")
    subprocess.run([
        "psql",
        "-h", "localhost",
        "-p", "5432",
        "-U", "postgres",
        "-c", "CREATE DATABASE cdb_staging;"
    ], check=True)
    
    return True

def run_migrations():
    """Apply Django migrations to create the schema."""
    print("\nApplying Django migrations...")
    
    # Set Django settings to use staging
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
    
    # Run migrations
    result = subprocess.run([
        "python", "manage.py", "migrate"
    ], check=False)
    
    if result.returncode != 0:
        print("Warning: There were issues with migrations, but we will continue setup...")
        return False
    
    print("Migrations completed successfully.")
    return True

def create_test_data():
    """Create essential test data."""
    print("\nCreating test data...")
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
    django.setup()
    
    # Import models now that Django is set up
    from cdb_app.models import MaterialClass, UnitLookup, Dataset
    from refresh_status.models import DatabaseStatus, RefreshLogEntry, StatusNotification
    
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
    print("Created material classes.")
    
    # Create units
    units = [
        {'unit_symbol': 'kg/m³', 'description': 'Kilograms per cubic meter'},
        {'unit_symbol': 'MPa', 'description': 'Megapascals'},
        {'unit_symbol': '%', 'description': 'Percent'},
        {'unit_symbol': 'mm', 'description': 'Millimeters'}
    ]
    
    for unit in units:
        UnitLookup.objects.get_or_create(
            unit_symbol=unit['unit_symbol'],
            defaults={'description': unit['description']}
        )
    print("Created units.")
    
    # Create sample datasets
    Dataset.objects.get_or_create(
        dataset_name='DS0',
        defaults={'license': 'Test dataset'}
    )
    
    Dataset.objects.get_or_create(
        dataset_name='DS_TEST',
        defaults={'license': 'Validation dataset for ETL testing'}
    )
    print("Created datasets.")
    
    # Create database status
    status = DatabaseStatus.objects.create(
        status=DatabaseStatus.IN_PROGRESS,
        read_only_mode=DatabaseStatus.READ_ONLY_ON,
        current_phase="Phase 3: Test Migration",
        current_step="Staging Database Reset",
        progress_percentage=10,
        maintenance_message="Database refresh testing in progress. The system is in read-only mode."
    )
    print("Created database status.")
    
    # Create log entries
    RefreshLogEntry.objects.create(
        phase="Phase 3: Test Migration",
        step="Staging Database Setup",
        status="info",
        message="Staging database prepared for ETL testing",
        is_error=False
    )
    print("Created log entry.")
    
    # Create notifications
    now = datetime.datetime.now()
    notification = StatusNotification.objects.create(
        title="Database Refresh Testing",
        message="We are currently testing the database refresh process. The application is in read-only mode.",
        notification_type=StatusNotification.INFO,
        is_active=True,
        start_display=now,
        end_display=now + datetime.timedelta(days=7),
        display_on_all_pages=True
    )
    print("Created notification.")
    
    return True

def main():
    print("\n===== PHASE 3: TEST MIGRATION - STAGING DATABASE RESET =====")
    print("This script will completely reset the staging database and prepare it for ETL testing.")
    
    try:
        # Step 1: Reset database
        if recreate_staging_database():
            print("[SUCCESS] Staging database reset successful")
        else:
            print("[ERROR] Failed to reset staging database")
            return False
        
        # Step 2: Apply migrations
        if run_migrations():
            print("[SUCCESS] Schema migrations successful")
        else:
            print("[WARNING] Migrations had issues but continuing setup...")
        
        # Give the database a moment to settle
        time.sleep(1)
        
        # Step 3: Create test data
        if create_test_data():
            print("[SUCCESS] Test data created successfully")
        else:
            print("[ERROR] Failed to create test data")
            return False
        
        print("\nPhase 3: Test Migration environment has been successfully set up!")
        print("The staging database has been reset and prepared for ETL testing.")
        print("Read-only mode is now active to simulate the protection during refresh.")
        
        return True
    except Exception as e:
        print(f"\nError in database setup: {str(e)}")
        return False

if __name__ == "__main__":
    main()
