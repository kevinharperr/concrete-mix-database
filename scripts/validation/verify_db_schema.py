"""Database Schema Verification Tool

This script verifies that the Django models in cdb_app/models.py align with the actual
database schema in the PostgreSQL database. It checks for:

1. Model to table name mapping
2. Field to column name mapping
3. Primary key field names
4. Relationship fields
5. Missing fields/columns

Usage: python verify_db_schema.py
"""

import os
import sys
import django
from django.db import connection
from django.apps import apps
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.db.models.fields import AutoField, BigAutoField
from collections import defaultdict

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Get the cdb_app models
cdb_app_models = apps.get_app_config('cdb_app').get_models()

def get_db_tables():
    """Get all tables in the database."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        return [row[0] for row in cursor.fetchall()]

def get_table_columns(table_name):
    """Get all columns for a table."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, [table_name])
        return {
            row[0]: {
                'data_type': row[1],
                'is_nullable': row[2],
                'default': row[3]
            } for row in cursor.fetchall()
        }

def get_table_constraints(table_name):
    """Get primary key and foreign key constraints for a table."""
    with connection.cursor() as cursor:
        # Get primary key
        cursor.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = 'public'
                AND tc.table_name = %s
                AND tc.constraint_type = 'PRIMARY KEY'
        """, [table_name])
        pk_columns = [row[0] for row in cursor.fetchall()]
        
        # Get foreign keys
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_schema = 'public'
                AND tc.table_name = %s
                AND tc.constraint_type = 'FOREIGN KEY'
        """, [table_name])
        fk_columns = {
            row[0]: {
                'foreign_table': row[1],
                'foreign_column': row[2]
            } for row in cursor.fetchall()
        }
        
        return {
            'primary_key': pk_columns,
            'foreign_keys': fk_columns
        }

def get_model_fields(model):
    """Get all fields for a model."""
    fields = {}
    for field in model._meta.get_fields():
        fields[field.name] = {
            'type': field.__class__.__name__,
            'is_relation': field.is_relation,
            'null': getattr(field, 'null', None),
            'unique': getattr(field, 'unique', None),
            'primary_key': getattr(field, 'primary_key', None),
            'db_column': getattr(field, 'db_column', None),
        }
        
        # Add related model info for relationship fields
        if field.is_relation:
            if hasattr(field, 'related_model') and field.related_model:
                fields[field.name]['related_model'] = field.related_model.__name__
                if hasattr(field, 'remote_field') and field.remote_field:
                    fields[field.name]['related_name'] = getattr(field.remote_field, 'related_name', None)
            
    return fields

def check_model_table_alignment():
    """Check alignment between models and database tables."""
    db_tables = get_db_tables()
    model_tables = {}
    issues = []
    
    print("\n=== CHECKING MODEL-TABLE ALIGNMENT ===")
    
    # Build a mapping of model names to expected table names
    for model in cdb_app_models:
        table_name = model._meta.db_table
        model_tables[model.__name__] = table_name
        
        # Check if the table exists in the database
        if table_name not in db_tables:
            issues.append(f"Model {model.__name__} maps to table '{table_name}' which doesn't exist in the database")
        else:
            print(f"[OK] Model {model.__name__} -> Table {table_name} (exists)")
    
    # Check for tables in the database that don't have a corresponding model
    django_system_tables = {
        'django_migrations', 'django_content_type', 'django_admin_log', 
        'django_session', 'auth_user', 'auth_group', 'auth_permission',
        'auth_group_permissions', 'auth_user_groups', 'auth_user_user_permissions',
        'django_site'
    }
    
    user_tables = set(db_tables) - django_system_tables
    missing_model_tables = user_tables - set(model_tables.values())
    
    if missing_model_tables:
        for table in missing_model_tables:
            issues.append(f"Table '{table}' exists in the database but has no corresponding model")
    
    return issues

def check_field_column_alignment():
    """Check alignment between model fields and table columns."""
    issues = []
    
    print("\n=== CHECKING FIELD-COLUMN ALIGNMENT ===")
    
    for model in cdb_app_models:
        model_fields = get_model_fields(model)
        table_name = model._meta.db_table
        print(f"\nModel {model.__name__} (Table: {table_name})")
        
        # Get table columns and constraints
        table_columns = get_table_columns(table_name)
        table_constraints = get_table_constraints(table_name)
        
        # Check primary key field
        pk_field_name = model._meta.pk.name
        db_pk_columns = table_constraints['primary_key']
        
        if db_pk_columns and pk_field_name:
            if len(db_pk_columns) == 1:
                expected_pk_column = pk_field_name
                if model_fields[pk_field_name]['db_column']:
                    expected_pk_column = model_fields[pk_field_name]['db_column']
                    
                if expected_pk_column != db_pk_columns[0]:
                    issues.append(f"Model {model.__name__}: Primary key field '{pk_field_name}' "  
                                 f"maps to column '{expected_pk_column}' but database uses '{db_pk_columns[0]}'")
                else:
                    print(f"  [OK] Primary key: {pk_field_name} -> {db_pk_columns[0]}")
            else:
                issues.append(f"Model {model.__name__} has a compound primary key in the database: {db_pk_columns}")
        
        # Check regular model fields against table columns
        for field_name, field_info in model_fields.items():
            # Skip many-to-many fields as they typically use a separate table
            if field_info['type'] == 'ManyToManyField':
                continue
                
            # Determine expected column name
            expected_column = field_name
            if field_info['db_column']:
                expected_column = field_info['db_column']
                
            # Foreign keys often have _id suffix in the actual column name
            if field_info['is_relation'] and field_info['type'] in ['ForeignKey', 'OneToOneField']:
                if expected_column == field_name and not expected_column.endswith('_id'):
                    expected_column = f"{field_name}_id"
            
            # Check if column exists
            if expected_column not in table_columns:
                issues.append(f"Model {model.__name__}: Field '{field_name}' (column '{expected_column}') "  
                             f"doesn't exist in table '{table_name}'")
            else:
                # Only show fields that map correctly
                print(f"  [OK] Field: {field_name} -> Column: {expected_column}")
                
                # Check if it's a foreign key and if the constraint is set up correctly
                if (field_info['is_relation'] and field_info['type'] in ['ForeignKey', 'OneToOneField'] 
                    and expected_column in table_constraints['foreign_keys']):
                    
                    fk_info = table_constraints['foreign_keys'][expected_column]
                    related_model = apps.get_model('cdb_app', field_info['related_model'])
                    expected_related_table = related_model._meta.db_table
                    
                    if fk_info['foreign_table'] != expected_related_table:
                        issues.append(f"Model {model.__name__}: Foreign key '{field_name}' should reference table "
                                     f"'{expected_related_table}' but references '{fk_info['foreign_table']}'")
        
        # Check for columns in the table that don't have a corresponding field
        model_db_columns = []
        for field_name, field_info in model_fields.items():
            expected_column = field_name
            if field_info['db_column']:
                expected_column = field_info['db_column']
                
            # Foreign keys often have _id suffix
            if field_info['is_relation'] and field_info['type'] in ['ForeignKey', 'OneToOneField']:
                if expected_column == field_name and not expected_column.endswith('_id'):
                    expected_column = f"{field_name}_id"
                    
            model_db_columns.append(expected_column)
        
        missing_fields = set(table_columns.keys()) - set(model_db_columns)
        if missing_fields:
            # Filter out some common metadata columns that Django might add
            common_meta_columns = {'id', 'created_at', 'updated_at', 'created', 'modified'}
            missing_fields = missing_fields - common_meta_columns
            
            if missing_fields:
                for column in missing_fields:
                    issues.append(f"Model {model.__name__}: Column '{column}' exists in table '{table_name}' but has no corresponding field")
    
    return issues

def check_relationship_fields():
    """Check relationship fields and their related_name attributes."""
    issues = []
    relationships = []
    
    print("\n=== CHECKING RELATIONSHIP FIELDS ===")
    
    for model in cdb_app_models:
        for field in model._meta.get_fields():
            if isinstance(field, (ForeignKey, OneToOneField)):
                related_name = field.remote_field.related_name if field.remote_field.related_name else f"{model.__name__.lower()}_set"
                relationships.append({
                    'model': model.__name__,
                    'field': field.name,
                    'related_model': field.related_model.__name__,
                    'related_name': related_name
                })
                print(f"[OK] {model.__name__}.{field.name} -> {field.related_model.__name__} (related_name: {related_name})")
    
    # Check for conflicting related_name values
    related_names = defaultdict(list)
    for rel in relationships:
        key = (rel['related_model'], rel['related_name'])
        related_names[key].append(rel)
    
    for (related_model, related_name), rels in related_names.items():
        if len(rels) > 1:
            issue = f"Multiple relationships use the same related_name '{related_name}' for model {related_model}:"
            for rel in rels:
                issue += f"\n  - {rel['model']}.{rel['field']}"
            issues.append(issue)
    
    return issues

def main():
    """Main function to run all checks."""
    print("\n===== DATABASE SCHEMA VERIFICATION TOOL =====")
    print(f"Checking models in cdb_app against the database schema...")
    
    all_issues = []
    all_issues.extend(check_model_table_alignment())
    all_issues.extend(check_field_column_alignment())
    all_issues.extend(check_relationship_fields())
    
    if all_issues:
        print("\n===== ISSUES FOUND =====")
        for i, issue in enumerate(all_issues, 1):
            print(f"Issue #{i}: {issue}")
        print(f"\nFound {len(all_issues)} issues that need to be resolved.")
    else:
        print("\n===== SUCCESS =====")
        print("All models in cdb_app align correctly with the database schema!")
        print("You can proceed with importing datasets.")
    
    return len(all_issues) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
