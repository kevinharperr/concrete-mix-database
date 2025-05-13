import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.contrib.admin.models import LogEntry
from django.db import transaction

def clean_remaining_content_types(confirm=True):
    # Get all content types for the retired app
    retired_cts = ContentType.objects.filter(app_label='concrete_mix_app')
    
    if not retired_cts.exists():
        print("No content types from retired app found. Nothing to clean.")
        return
        
    print(f"Found {retired_cts.count()} content types from retired 'concrete_mix_app':")
    for ct in retired_cts:
        print(f"  - {ct.app_label}.{ct.model} (ID: {ct.id})")
    
    # Ask for confirmation if needed
    if confirm:
        confirmation = input("\nDo you want to proceed with cleaning up these content types? (y/n): ").strip().lower()
        if confirmation != 'y':
            print("Operation cancelled.")
            return
    
    print("\nStarting cleanup process...")
    
    # Track statistics
    perms_deleted = 0
    logs_updated = 0
    cts_deleted = 0
    
    # Use a transaction to ensure atomicity
    with transaction.atomic():
        for ct in retired_cts:
            print(f"\nProcessing {ct.app_label}.{ct.model} (ID: {ct.id})")
            
            # Delete permissions
            perms = Permission.objects.filter(content_type=ct)
            if perms.exists():
                count = perms.count()
                print(f"  - Deleting {count} permissions")
                perms.delete()
                perms_deleted += count
            else:
                print("  - No permissions to delete")
            
            # Check for admin log entries
            logs = LogEntry.objects.filter(content_type=ct)
            if logs.exists():
                count = logs.count()
                print(f"  - Found {count} admin log entries. These will be deleted when the content type is deleted.")
                logs_updated += count
            
            # Delete the content type
            print(f"  - Deleting content type {ct.app_label}.{ct.model}")
            ct.delete()
            cts_deleted += 1
    
    print("\nCleanup complete!")
    print(f"Summary:")
    print(f"  - {perms_deleted} permissions deleted")
    print(f"  - {logs_updated} admin log entries affected")
    print(f"  - {cts_deleted} content types deleted")
    print(f"\nRemaining content types from 'concrete_mix_app': {ContentType.objects.filter(app_label='concrete_mix_app').count()}")

if __name__ == "__main__":
    # If run with --force, skip confirmation
    force = len(sys.argv) > 1 and sys.argv[1] == '--force'
    clean_remaining_content_types(confirm=not force)
