"""
Template tags for the refresh_status app.

These tags allow templates to check if the system is in read-only mode.
"""
from django import template
from refresh_status.models import DatabaseStatus

register = template.Library()

@register.simple_tag
def is_read_only_mode():
    """
    Check if the database is currently in read-only mode.
    
    Returns:
        bool: True if read-only mode is active, False otherwise
    """
    try:
        status = DatabaseStatus.objects.latest('last_updated')
        return status.read_only_mode == DatabaseStatus.READ_ONLY_ON
    except DatabaseStatus.DoesNotExist:
        return False

@register.inclusion_tag('includes/read_only_indicator.html')
def read_only_indicator():
    """
    Render a read-only mode indicator if the system is in read-only mode.
    
    Returns:
        dict: Context for the read_only_indicator template
    """
    try:
        status = DatabaseStatus.objects.latest('last_updated')
        is_read_only = status.read_only_mode == DatabaseStatus.READ_ONLY_ON
        maintenance_message = status.maintenance_message if is_read_only else ""
    except DatabaseStatus.DoesNotExist:
        is_read_only = False
        maintenance_message = ""
        
    return {
        'is_read_only': is_read_only,
        'maintenance_message': maintenance_message
    }
