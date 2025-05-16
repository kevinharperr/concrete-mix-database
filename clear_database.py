#!/usr/bin/env python
"""
Database clearing utility for the Concrete Mix Database refresh.

This script carefully clears all data tables while preserving the schema structure
and minimum required lookup values to keep the web application functional.
"""
import os
import sys
import django
import datetime
import argparse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from django.db import connection
from cdb_app.models import (
    UnitLookup, PropertyDictionary, MaterialClass, Standard, TestMethod,
    CuringRegime, Dataset, BibliographicReference, Material, ConcreteMix,
    ConcreteMixReference, MixComponent, Specimen, PerformanceResult,
    SustainabilityMetric, MaterialProperty, CementDetail, ScmDetail,
    AggregateDetail, AggregateConstituent, AdmixtureDetail, FibreDetail,
    ColumnMap
)

def clear_data_tables(preserve_lookups=True, preserve_auth=True):
    """
    Clear all data tables while preserving schema structure.
    
    Args:
        preserve_lookups (bool): If True, preserves essential lookup table entries
        preserve_auth (bool): If True, preserves Django authentication tables
    """
    # Create timestamp for logging
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\nStarting database clearing process at {timestamp}")
    
    # Track table clearing results
    results = {}
    
    # List of Django auth tables to preserve if requested
    auth_tables = ['auth_user', 'auth_group', 'auth_permission', 
                   'auth_user_groups', 'auth_user_user_permissions', 
                   'auth_group_permissions', 'django_content_type',
                   'django_admin_log', 'django_session']
    
    print(f"Auth tables preservation: {'ENABLED' if preserve_auth else 'DISABLED'}")
    print(f"Lookup tables preservation: {'ENABLED' if preserve_lookups else 'DISABLED'}")
    
    try:
        # If preserving auth tables, check if we need to temporarily disable foreign key constraints
        if preserve_auth and connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                print("\n--- Temporarily disabling foreign key constraints ---")
                cursor.execute("SET session_replication_role = 'replica';")
                
        # Clear data tables in reverse dependency order
        
        # First the detail tables (one-to-one relationships with Material)
        print("\n--- Clearing Material Detail Tables ---")
        results["FibreDetail"] = FibreDetail.objects.all().delete()
        results["AdmixtureDetail"] = AdmixtureDetail.objects.all().delete()
        results["AggregateConstituent"] = AggregateConstituent.objects.all().delete()
        results["AggregateDetail"] = AggregateDetail.objects.all().delete()
        results["ScmDetail"] = ScmDetail.objects.all().delete()
        results["CementDetail"] = CementDetail.objects.all().delete()
        
        # Then property and performance data
        print("\n--- Clearing Property and Performance Data ---")
        results["MaterialProperty"] = MaterialProperty.objects.all().delete()
        results["SustainabilityMetric"] = SustainabilityMetric.objects.all().delete()
        results["PerformanceResult"] = PerformanceResult.objects.all().delete()
        results["Specimen"] = Specimen.objects.all().delete()
        
        # Then mix components and relationships
        print("\n--- Clearing Mix Components and References ---")
        results["MixComponent"] = MixComponent.objects.all().delete()
        results["ConcreteMixReference"] = ConcreteMixReference.objects.all().delete()
        
        # Then core data tables
        print("\n--- Clearing Core Data Tables ---")
        results["ConcreteMix"] = ConcreteMix.objects.all().delete()
        results["Material"] = Material.objects.all().delete()
        results["BibliographicReference"] = BibliographicReference.objects.all().delete()
        
        # Then utility tables
        print("\n--- Clearing Utility Tables ---")
        results["ColumnMap"] = ColumnMap.objects.all().delete()
        
        # Handle lookup tables based on preserve_lookups flag
        if not preserve_lookups:
            print("\n--- Clearing Lookup Tables ---")
            results["CuringRegime"] = CuringRegime.objects.all().delete()
            results["TestMethod"] = TestMethod.objects.all().delete()
            results["Standard"] = Standard.objects.all().delete()
            results["MaterialClass"] = MaterialClass.objects.all().delete()
            results["PropertyDictionary"] = PropertyDictionary.objects.all().delete()
            results["UnitLookup"] = UnitLookup.objects.all().delete()
            results["Dataset"] = Dataset.objects.all().delete()
        else:
            print("\n--- Preserving Lookup Tables ---")
            print("Lookup tables (UnitLookup, PropertyDictionary, MaterialClass, etc.) have been preserved.")
            print("This ensures the web application can still function with empty data tables.")
            
        # Reset sequences if needed (PostgreSQL)
        if connection.vendor == 'postgresql':
            print("\n--- Resetting Sequences ---")
            with connection.cursor() as cursor:
                # Define the primary key columns for each table
                sequence_resets = [
                    {'table': 'concrete_mix', 'column': 'mix_id'},
                    {'table': 'material', 'column': 'material_id'},
                    {'table': 'bibliographic_reference', 'column': 'reference_id'},
                    {'table': 'specimen', 'column': 'specimen_id'},
                    {'table': 'performance_result', 'column': 'result_id'},
                    {'table': 'material_property', 'column': 'property_id'},
                    {'table': 'sustainability_metric', 'column': 'metric_id'},
                    {'table': 'mix_component', 'column': 'component_id'}
                ]
                
                # Reset each sequence
                for item in sequence_resets:
                    try:
                        cursor.execute(f"SELECT setval(pg_get_serial_sequence('{item['table']}', '{item['column']}'), 1, false);")
                        print(f"Reset sequence for {item['table']}.{item['column']}")
                    except Exception as e:
                        print(f"Could not reset sequence for {item['table']}.{item['column']}: {str(e)}")
            
            print("PostgreSQL sequence reset completed.")

        
        print("\n--- Results Summary ---")
        for table, count in results.items():
            print(f"Cleared {table}: {count}")
            
        # Re-enable foreign key constraints if they were disabled
        if preserve_auth and connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                print("\n--- Re-enabling foreign key constraints ---")
                cursor.execute("SET session_replication_role = 'origin';")
        
        print("\nDatabase clearing completed successfully.")
        
        # Create essential lookup values if all were cleared
        if not preserve_lookups:
            print("\n--- Creating Minimal Required Lookup Values ---")
            create_essential_lookups()
            
        return True
        
    except Exception as e:
        print(f"\nError during database clearing: {str(e)}")
        return False

def create_essential_lookups():
    """Create minimal required lookup values for the app to function."""
    # Create essential MaterialClass entries
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
    
    # Create essential UnitLookup entries
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
    
    # Create at least one dataset
    Dataset.objects.get_or_create(
        dataset_name='DS0',
        defaults={'license': 'Internal test dataset'}
    )
    
    print("Essential lookup values created successfully.")

def main():
    parser = argparse.ArgumentParser(description='Clear Concrete Mix Database data')
    parser.add_argument('--clear-all', action='store_true', 
                        help='Clear all tables including lookup tables')
    parser.add_argument('--clear-auth', action='store_true',
                        help='Also clear authentication tables (users, groups, permissions)')
    parser.add_argument('--confirm', action='store_true',
                        help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Warn about this being a destructive operation
    if not args.confirm:
        print("\n⚠️ WARNING: This will delete all concrete mix data from the database! ⚠️")
        print("This operation cannot be undone. Make sure you have a backup.")
        
        confirm = input("\nAre you sure you want to continue? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return
    
    # Clear the database
    success = clear_data_tables(preserve_lookups=not args.clear_all, preserve_auth=not args.clear_auth)
    
    if success:
        print("\nThe database has been cleared successfully.")
        print("The web application should still be functional but with no data.")
        print("You can now start the fresh import process.")
    else:
        print("\nDatabase clearing encountered errors. Please check the logs.")

if __name__ == "__main__":
    main()
