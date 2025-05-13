# concrete_mix_app/management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from concrete_mix_app.models import (
    Material, Concretemix, Mixcomposition, 
    Performanceresult, Durabilityresult, Sustainabilitymetrics,
    Specimen, UserObjectTracking
)


class Command(BaseCommand):
    help = 'Creates default permission groups for the concrete mix application'

    def handle(self, *args, **options):
        # Create groups
        admin_group, created = Group.objects.get_or_create(name='Admins')
        contributors_group, created = Group.objects.get_or_create(name='Data Contributors')
        viewers_group, created = Group.objects.get_or_create(name='Viewers')
        
        # Handle migration from old group name if it exists
        try:
            old_editors_group = Group.objects.get(name='Editors')
            # Transfer members from old to new group if needed
            for user in old_editors_group.user_set.all():
                user.groups.add(contributors_group)
                self.stdout.write(f'Transferred user {user.username} to Data Contributors group')
            # Don't delete old group immediately to avoid breaking existing code
            # This can be removed in future after migration is complete
        except Group.DoesNotExist:
            pass

        self.stdout.write(f"Groups created or verified.")

        # Define permissions for each model
        models_permissions = {
            Material: ['add', 'change', 'delete', 'view'],
            Concretemix: ['add', 'change', 'delete', 'view'],
            Mixcomposition: ['add', 'change', 'delete', 'view'],
            Performanceresult: ['add', 'change', 'delete', 'view'],
            Durabilityresult: ['add', 'change', 'delete', 'view'],
            Sustainabilitymetrics: ['add', 'change', 'delete', 'view'],
            Specimen: ['add', 'change', 'delete', 'view'],
            UserObjectTracking: ['view'],
        }

        # Set permissions for each group
        self._set_group_permissions(admin_group, models_permissions, full_access=True)
        
        # Data Contributors can add and change any model but can only delete their own content
        contributor_permissions = {model: ['add', 'change', 'view'] for model, perms in models_permissions.items()}
        self._set_group_permissions(contributors_group, contributor_permissions)
        
        # Viewers can only view data
        viewer_permissions = {model: ['view'] for model, perms in models_permissions.items()}
        self._set_group_permissions(viewers_group, viewer_permissions)

        self.stdout.write(self.style.SUCCESS('Permission groups successfully set up!'))

    def _set_group_permissions(self, group, models_permissions, full_access=False):
        """
        Set permissions for a group based on the specified models and permission types.
        
        If full_access is True, all permissions for the models will be granted.
        """
        # Clear existing permissions
        group.permissions.clear()
        
        # Assign new permissions
        for model, permission_types in models_permissions.items():
            content_type = ContentType.objects.get_for_model(model)
            
            for permission_type in permission_types:
                codename = f"{permission_type}_{model._meta.model_name}"
                try:
                    permission = Permission.objects.get(content_type=content_type, codename=codename)
                    group.permissions.add(permission)
                    self.stdout.write(f"Added {permission.codename} to {group.name}")
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission {codename} does not exist"))
                    
        # Save the group
        group.save()
