import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType

def clean_content_types():
    # Print stats before cleaning
    print("Content types before cleaning:")
    print(f"Total content types: {ContentType.objects.count()}")
    print(f"concrete_mix_app content types: {ContentType.objects.filter(app_label='concrete_mix_app').count()}")
    print(f"cdb_app content types: {ContentType.objects.filter(app_label='cdb_app').count()}")
    
    # Get all content types for the retired app
    retired_cts = ContentType.objects.filter(app_label='concrete_mix_app')
    
    if not retired_cts.exists():
        print("No content types from retired app found. Nothing to clean.")
        return
        
    print(f"\nFound {retired_cts.count()} content types from retired 'concrete_mix_app':")
    
    # For each retired content type, check if there's a corresponding one in cdb_app
    for ct in retired_cts:
        print(f"- {ct.app_label}.{ct.model}")
        
        # Try to find equivalent content type in cdb_app
        try:
            new_ct = ContentType.objects.get(app_label='cdb_app', model=ct.model)
            print(f"  Found matching content type in cdb_app (ID: {new_ct.id})")
            
            # Check for any objects that might still be using the old content type
            # This includes permissions, admin log entries, etc.
            from django.contrib.auth.models import Permission
            from django.contrib.admin.models import LogEntry
            
            # Fix permissions
            perms = Permission.objects.filter(content_type=ct)
            if perms.exists():
                print(f"  Updating {perms.count()} permissions to use new content type")
                for perm in perms:
                    # Check if the permission already exists for the new content type
                    existing = Permission.objects.filter(
                        content_type=new_ct,
                        codename=perm.codename
                    ).first()
                    
                    if existing:
                        print(f"    Permission {perm.codename} already exists for new content type, deleting old one")
                        perm.delete()
                    else:
                        print(f"    Updating permission {perm.codename} to use new content type")
                        perm.content_type = new_ct
                        perm.save()
            
            # Fix admin log entries
            logs = LogEntry.objects.filter(content_type=ct)
            if logs.exists():
                print(f"  Updating {logs.count()} admin log entries to use new content type")
                logs.update(content_type=new_ct)
            
            # Now we can safely remove the old content type
            print(f"  Deleting content type {ct.app_label}.{ct.model}")
            ct.delete()
            
        except ContentType.DoesNotExist:
            print(f"  No matching content type in cdb_app. This model might have been renamed or removed.")
            print(f"  Consider if any data is still associated with this content type before deleting it.")
    
    # Print stats after cleaning
    print("\nContent types after cleaning:")
    print(f"Total content types: {ContentType.objects.count()}")
    print(f"concrete_mix_app content types: {ContentType.objects.filter(app_label='concrete_mix_app').count()}")
    print(f"cdb_app content types: {ContentType.objects.filter(app_label='cdb_app').count()}")

if __name__ == "__main__":
    clean_content_types()
