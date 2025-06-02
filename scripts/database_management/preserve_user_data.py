#!/usr/bin/env python
"""
User data preservation utility for the Concrete Mix Database refresh.

This script exports and imports user authentication data to preserve user access
during the database refresh process.
"""
import os
import sys
import django
import json
import datetime
import argparse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

def export_user_data(output_file=None):
    """
    Export all user-related data to a JSON file.
    
    Args:
        output_file (str): Path to the output JSON file. If not provided,
                          a timestamped filename will be generated.
    
    Returns:
        str: Path to the created JSON file
    """
    if not output_file:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"user_data_export_{timestamp}.json"
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Exporting user data to {output_file}...")
    
    # Export user data
    users = []
    for user in User.objects.all():
        user_data = {
            'username': user.username,
            'password': user.password,  # This is the hashed password
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'groups': [g.name for g in user.groups.all()],
            'user_permissions': [f"{p.content_type.app_label}.{p.codename}" for p in user.user_permissions.all()]
        }
        users.append(user_data)
    
    # Export group data
    groups = []
    for group in Group.objects.all():
        group_data = {
            'name': group.name,
            'permissions': [f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()]
        }
        groups.append(group_data)
    
    # Export content types and permissions
    content_types = []
    for ct in ContentType.objects.all():
        ct_data = {
            'app_label': ct.app_label,
            'model': ct.model,
        }
        content_types.append(ct_data)
    
    permissions = []
    for perm in Permission.objects.all():
        perm_data = {
            'codename': perm.codename,
            'name': perm.name,
            'content_type': {
                'app_label': perm.content_type.app_label,
                'model': perm.content_type.model
            }
        }
        permissions.append(perm_data)
    
    # Combine all data into a single export
    export_data = {
        'export_date': datetime.datetime.now().isoformat(),
        'users': users,
        'groups': groups,
        'content_types': content_types,
        'permissions': permissions
    }
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Exported {len(users)} users, {len(groups)} groups, {len(permissions)} permissions")
    print(f"User data exported successfully to {output_file}")
    
    return output_file

def import_user_data(input_file):
    """
    Import user data from a JSON file.
    
    Args:
        input_file (str): Path to the input JSON file
        
    Returns:
        bool: True if import was successful, False otherwise
    """
    try:
        print(f"Importing user data from {input_file}...")
        
        # Read the JSON file
        with open(input_file, 'r') as f:
            import_data = json.load(f)
        
        # First recreate content types if needed
        for ct_data in import_data.get('content_types', []):
            ContentType.objects.get_or_create(
                app_label=ct_data['app_label'],
                model=ct_data['model']
            )
        
        # Then recreate permissions
        for perm_data in import_data.get('permissions', []):
            content_type = ContentType.objects.get(
                app_label=perm_data['content_type']['app_label'],
                model=perm_data['content_type']['model']
            )
            
            Permission.objects.get_or_create(
                codename=perm_data['codename'],
                content_type=content_type,
                defaults={'name': perm_data['name']}
            )
        
        # Create groups
        for group_data in import_data.get('groups', []):
            group, created = Group.objects.get_or_create(name=group_data['name'])
            
            # Add permissions to group
            for perm_str in group_data.get('permissions', []):
                app_label, codename = perm_str.split('.')
                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    print(f"Warning: Permission {perm_str} not found")
        
        # Create users
        for user_data in import_data.get('users', []):
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_active': user_data['is_active'],
                    'is_staff': user_data['is_staff'],
                    'is_superuser': user_data['is_superuser'],
                    'password': user_data['password']  # Already hashed
                }
            )
            
            if not created:
                # Update existing user
                user.email = user_data['email']
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.is_active = user_data['is_active']
                user.is_staff = user_data['is_staff']
                user.is_superuser = user_data['is_superuser']
                user.password = user_data['password']
                user.save()
            
            # Parse date strings
            if user_data.get('date_joined'):
                user.date_joined = datetime.datetime.fromisoformat(user_data['date_joined'])
            if user_data.get('last_login'):
                user.last_login = datetime.datetime.fromisoformat(user_data['last_login'])
            user.save()
            
            # Clear existing groups and add the ones from the export
            user.groups.clear()
            for group_name in user_data.get('groups', []):
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                except Group.DoesNotExist:
                    print(f"Warning: Group {group_name} not found")
            
            # Clear existing permissions and add the ones from the export
            user.user_permissions.clear()
            for perm_str in user_data.get('user_permissions', []):
                app_label, codename = perm_str.split('.')
                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    user.user_permissions.add(perm)
                except Permission.DoesNotExist:
                    print(f"Warning: Permission {perm_str} not found")
        
        print(f"Successfully imported {len(import_data.get('users', []))} users")
        print(f"Successfully imported {len(import_data.get('groups', []))} groups")
        return True
    
    except Exception as e:
        print(f"Error importing user data: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Export/import user data for database refresh')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export user data')
    export_parser.add_argument('--output', type=str, help='Output file path')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import user data')
    import_parser.add_argument('--input', type=str, required=True, help='Input file path')
    
    args = parser.parse_args()
    
    if args.command == 'export':
        export_user_data(args.output)
    elif args.command == 'import':
        import_user_data(args.input)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
