import os
import django
import sys
from django.db import connections

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.contrib.admin.models import LogEntry
from django.db.models import Q

def audit_content_types():
    # Get all content types for the retired app
    retired_cts = ContentType.objects.filter(app_label='concrete_mix_app')
    
    if not retired_cts.exists():
        print("No content types from retired app found.")
        return
        
    print(f"Found {retired_cts.count()} content types from retired 'concrete_mix_app':")
    print("\nAuditing each content type for relationships...\n")
    print("=" * 80)
    
    # For each retired content type, check for relationships
    for ct in retired_cts:
        ct_id = ct.id
        print(f"\nContent Type: {ct.app_label}.{ct.model} (ID: {ct_id})")
        print("-" * 50)
        
        # Check for permissions
        perms = Permission.objects.filter(content_type=ct)
        if perms.exists():
            print(f"[OK] Found {perms.count()} permissions using this content type:")
            for perm in perms:
                print(f"  - {perm.codename}: {perm.name}")
        else:
            print("[OK] No permissions using this content type")
            
        # Check for admin log entries
        logs = LogEntry.objects.filter(content_type=ct)
        if logs.exists():
            print(f"[OK] Found {logs.count()} admin log entries using this content type")
        else:
            print("[OK] No admin log entries using this content type")
            
        # Check for generic relations - this requires a more comprehensive search
        # We'll use raw SQL to search for this content type ID in all tables
        print("\nSearching for generic relation references...")
        
        # Get database cursor
        with connections['default'].cursor() as cursor:
            # Get all tables in the database
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            found_relations = False
            
            # For each table, check for columns that might contain the content type ID
            for table in tables:
                # Skip the contenttypes table itself and the tables we already checked
                if table in ['django_content_type', 'auth_permission', 'django_admin_log']:
                    continue
                    
                # Get columns for this table
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                """)
                columns = [row[0] for row in cursor.fetchall()]
                
                # Check which columns might be integer type and could reference content types
                integer_columns = []
                for col in columns:
                    if '_id' in col.lower() or col.lower() in ['id', 'content_type_id', 'object_id']:
                        integer_columns.append(col)
                
                # If no potential integer columns, skip this table
                if not integer_columns:
                    continue
                    
                # Check each integer column for references to this content type ID
                for col in integer_columns:
                    try:
                        # Skip non-numeric columns
                        cursor.execute(f"""
                            SELECT data_type 
                            FROM information_schema.columns 
                            WHERE table_name = '{table}' AND column_name = '{col}'
                        """)
                        data_type = cursor.fetchone()[0]
                        if not data_type.startswith('int') and not data_type.startswith('big'):
                            continue
                            
                        # Check if this column contains the content type ID
                        query = f"SELECT COUNT(*) FROM {table} WHERE {col} = {ct_id}"
                        cursor.execute(query)
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            print(f"  ! FOUND {count} references in {table}.{col}")
                            
                            # Get sample data
                            cursor.execute(f"SELECT * FROM {table} WHERE {col} = {ct_id} LIMIT 3")
                            samples = cursor.fetchall()
                            
                            # Get column names for the sample data
                            cursor.execute(f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}' 
                                ORDER BY ordinal_position
                            """)
                            sample_cols = [row[0] for row in cursor.fetchall()]
                            
                            print(f"    Sample data:")
                            for sample in samples:
                                sample_dict = {sample_cols[i]: sample[i] for i in range(len(sample_cols))}
                                print(f"    {sample_dict}")
                                
                            found_relations = True
                    except Exception as e:
                        print(f"    Error checking {table}.{col}: {str(e)}")
            
            if not found_relations:
                print("  [OK] No generic relation references found")
    
    print("\n" + "=" * 80)
    print("Audit complete! Please review the findings above before removing any content types.")

if __name__ == "__main__":
    audit_content_types()
