# concrete_mix_app/utils.py
from .models import UserObjectTracking

def track_object_creation(user, model_instance):
    """
    Track object creation by a user without modifying the object itself.
    
    Args:
        user: The User who created the object
        model_instance: The model instance that was created
        
    Returns:
        The UserObjectTracking instance
    """
    if not user or user.is_anonymous:
        return None
        
    # Get the model name and object ID
    content_type = model_instance.__class__.__name__
    object_id = model_instance.pk
    
    # Create or update the tracking record
    tracking, created = UserObjectTracking.objects.update_or_create(
        content_type=content_type,
        object_id=object_id,
        defaults={'created_by': user}
    )
    
    return tracking

def get_object_creator(model_instance):
    """
    Get the user who created an object, if tracked.
    
    Args:
        model_instance: The model instance to check
        
    Returns:
        The User who created the object, or None if not tracked
    """
    content_type = model_instance.__class__.__name__
    object_id = model_instance.pk
    
    try:
        tracking = UserObjectTracking.objects.get(
            content_type=content_type,
            object_id=object_id
        )
        return tracking.created_by
    except UserObjectTracking.DoesNotExist:
        return None

def user_can_edit_object(user, model_instance):
    """
    Check if a user has permission to edit an object.
    Permission is granted if:
    1. User is a superuser
    2. User created the object
    3. User is in the 'Admins' group
    4. User is in the 'Data Contributors' group (legacy 'Editors' group is also checked for compatibility)
    
    Args:
        user: The User to check
        model_instance: The model instance to check permission for
        
    Returns:
        Boolean indicating if the user can edit the object
    """
    if user.is_superuser:
        return True
        
    # Check if user created the object
    creator = get_object_creator(model_instance)
    if creator and creator == user:
        return True
        
    # Check if user is in Admins group
    if user.groups.filter(name='Admins').exists():
        return True
        
    # Check if user is in Data Contributors group
    if user.groups.filter(name='Data Contributors').exists():
        return True
        
    # Legacy check for backward compatibility
    if user.groups.filter(name='Editors').exists():
        return True
        
    return False


def user_can_contribute_data(user):
    """
    Check if a user has permission to contribute data.
    Permission is granted if:
    1. User is a superuser
    2. User is in the 'Admins' group
    3. User is in the 'Data Contributors' group (legacy 'Editors' group is also checked for compatibility)
    
    Args:
        user: The User to check
        
    Returns:
        Boolean indicating if the user can contribute data
    """
    if user.is_superuser:
        return True
        
    # Check if user is in Admins group
    if user.groups.filter(name='Admins').exists():
        return True
        
    # Check if user is in Data Contributors group
    if user.groups.filter(name='Data Contributors').exists():
        return True
        
    # Legacy check for backward compatibility
    if user.groups.filter(name='Editors').exists():
        return True
        
    return False
