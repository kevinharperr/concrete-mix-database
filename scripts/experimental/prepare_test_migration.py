#!/usr/bin/env python
"""
Prepare the staging environment for Phase 3: Test Migration.

This script sets up a test database status and creates 
minimal data needed to test the ETL process.
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings_staging')
django.setup()

# Import Django models
from cdb_app.models import UnitLookup, MaterialClass, Dataset
from refresh_status.models import DatabaseStatus, RefreshLogEntry, StatusNotification

def create_test_data():
    """Create essential test data for the ETL process."""
    print(f"\nCreating test data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
    return True

def setup_refresh_status():
    """Set up the refresh status system."""
    print("\nSetting up refresh status...")
    
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
    notification = StatusNotification.objects.create(
        title="Database Refresh Testing",
        message="We are currently testing the database refresh process. The application is in read-only mode.",
        notification_type=StatusNotification.INFO,
        is_active=True,
        display_until=datetime.now() + timedelta(days=7),
        display_on="all"
    )
    print("Created notification.")
    return True

def main():
    print("\n===== PHASE 3: TEST MIGRATION PREPARATION =====")
    print("This script will set up the staging environment for testing the ETL process.")
    
    try:
        create_test_data()
        setup_refresh_status()
        
        print("\nTest environment is ready for Phase 3: Test Migration!")
        print("The system is now in read-only mode.")
        print("You can proceed with testing the ETL framework.")
        return True
    except Exception as e:
        print(f"Error setting up test environment: {str(e)}")
        return False

if __name__ == "__main__":
    main()
