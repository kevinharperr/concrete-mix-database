"""
Context processors for the refresh_status app.

These processors add system notifications and database status to the context of all templates.
"""
from django.utils import timezone
from django.db.models import Q
from .models import StatusNotification, DatabaseStatus, RefreshLogEntry

def refresh_status(request):
    """
    Add database refresh status and notifications to the template context.
    This allows maintenance notifications to be displayed on all pages and enables
    status indicators in the UI when necessary.
    """
    # Get database status
    try:
        db_status = DatabaseStatus.objects.get(pk=1)
        maintenance_mode_active = db_status.read_only_mode == 'on' or db_status.status == 'in_progress'
    except DatabaseStatus.DoesNotExist:
        db_status = None
        maintenance_mode_active = False
        
    # Filter for active notifications that should be displayed now
    now = timezone.now()
    notifications = StatusNotification.objects.filter(
        Q(is_active=True) & 
        Q(start_display__lte=now) & 
        (Q(end_display__isnull=True) | Q(end_display__gte=now))
    ).order_by('-display_order', '-created_at')
    
    # Filter further for current page if specific targeting is enabled
    current_path = request.path
    page_notifications = []
    
    for notification in notifications:
        # Check if notification applies to this page
        if notification.display_on_all_pages:
            page_notifications.append(notification)
        elif notification.specific_pages:
            # Check if current path matches any of the specific pages
            pages = [p.strip() for p in notification.specific_pages.split(',')]
            if any(current_path.startswith(page) for page in pages):
                page_notifications.append(notification)
    
    # Get recent log entries
    recent_log_entries = []
    if maintenance_mode_active:
        recent_log_entries = RefreshLogEntry.objects.order_by('-timestamp')[:5]
    
    return {
        'notifications': page_notifications,
        'maintenance_mode_active': maintenance_mode_active,
        'db_status': db_status,
        'recent_log_entries': recent_log_entries,
    }
