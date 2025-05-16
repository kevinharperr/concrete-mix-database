"""
Context processors for the refresh_status app.

These processors add system notifications to the context of all templates.
"""
from .models import StatusNotification

def refresh_notifications(request):
    """
    Add active system notifications to the template context.
    This allows notifications to be displayed on all pages.
    """
    # Filter for active notifications
    notifications = StatusNotification.objects.filter(is_active=True)
    
    # Filter further for current page if specific targeting is enabled
    current_path = request.path
    page_notifications = []
    
    for notification in notifications:
        # Check if notification should be displayed
        if not notification.is_displayed():
            continue
            
        # Check if notification applies to this page
        if notification.display_on_all_pages:
            page_notifications.append(notification)
        elif notification.specific_pages:
            # Check if current path matches any of the specific pages
            pages = [p.strip() for p in notification.specific_pages.split(',')]
            if any(current_path.startswith(page) for page in pages):
                page_notifications.append(notification)
    
    return {
        'notifications': page_notifications,
    }
