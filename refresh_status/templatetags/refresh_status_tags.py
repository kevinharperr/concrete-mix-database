"""
Template tags for the refresh_status app.

These tags allow templates to check database status and display maintenance indicators.
"""
from django import template
from django.utils import timezone
from refresh_status.models import DatabaseStatus, RefreshLogEntry

register = template.Library()

@register.filter
def modulo(value, arg):
    """
    Return the modulo of value and arg.
    
    Example: {{ value|modulo:60 }} - Returns remainder when value is divided by 60
    """
    try:
        return int(value) % int(arg)
    except (ValueError, TypeError):
        return 0
        
@register.filter
def divisibleby(value, arg):
    """
    Return the integer division of value by arg.
    
    Example: {{ value|divisibleby:60 }} - Returns how many times 60 goes into value
    """
    try:
        return int(value) // int(arg)
    except (ValueError, TypeError):
        return 0

@register.simple_tag
def is_read_only_mode():
    """
    Check if the database is currently in read-only mode.
    
    Returns:
        bool: True if read-only mode is active, False otherwise
    """
    try:
        status = DatabaseStatus.objects.get(pk=1)
        return status.read_only_mode == DatabaseStatus.READ_ONLY_ON
    except DatabaseStatus.DoesNotExist:
        return False
        
@register.simple_tag
def is_maintenance_active():
    """
    Check if database maintenance is currently active (either in read-only mode or in-progress).
    
    Returns:
        bool: True if maintenance is active, False otherwise
    """
    try:
        status = DatabaseStatus.objects.get(pk=1)
        return (status.read_only_mode == DatabaseStatus.READ_ONLY_ON or 
                status.status == DatabaseStatus.IN_PROGRESS)
    except DatabaseStatus.DoesNotExist:
        return False

@register.inclusion_tag('includes/read_only_indicator.html')
def read_only_indicator():
    """
    Render a maintenance status indicator if the system is in read-only mode or undergoing refresh.
    
    Returns:
        dict: Context for the read_only_indicator template
    """
    try:
        status = DatabaseStatus.objects.get(pk=1)
        is_read_only = status.read_only_mode == DatabaseStatus.READ_ONLY_ON
        is_in_progress = status.status == DatabaseStatus.IN_PROGRESS
        maintenance_active = is_read_only or is_in_progress
        
        # Get estimated time remaining if applicable
        time_remaining = None
        if is_in_progress and status.estimated_completion:
            now = timezone.now()
            if now < status.estimated_completion:
                # Calculate remaining time in minutes
                delta = status.estimated_completion - now
                time_remaining = int(delta.total_seconds() / 60)
        
        # Get latest log entry for additional context
        latest_log = None
        if is_in_progress:
            try:
                latest_log = RefreshLogEntry.objects.order_by('-timestamp')[0]
            except (RefreshLogEntry.DoesNotExist, IndexError):
                pass
                
    except DatabaseStatus.DoesNotExist:
        maintenance_active = False
        is_read_only = False
        is_in_progress = False
        time_remaining = None
        latest_log = None
        
    return {
        'maintenance_active': maintenance_active,
        'is_read_only': is_read_only,
        'is_in_progress': is_in_progress,
        'maintenance_message': status.maintenance_message if maintenance_active and hasattr(status, 'maintenance_message') else "",
        'progress_percentage': status.progress_percentage if is_in_progress and hasattr(status, 'progress_percentage') else 0,
        'time_remaining': time_remaining,
        'latest_log': latest_log
    }
