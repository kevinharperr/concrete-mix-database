from django.urls import path
# Import status page views directly from the status_views module
from refresh_status.views.status_views import (
    StatusPageView, 
    AdminStatusView, 
    update_status, 
    get_status_json
)
# Import notification views from the notification_views module
from refresh_status.views.notification_views import (
    manage_notifications,
    create_notification,
    toggle_notification,
    delete_notification,
    schedule_maintenance
)

app_name = 'refresh_status'

urlpatterns = [
    # Status pages
    path('', StatusPageView.as_view(), name='status'),
    path('admin/', AdminStatusView.as_view(), name='admin_status'),
    
    # API endpoints
    path('api/update/', update_status, name='update_status'),
    path('api/status/', get_status_json, name='get_status_json'),
    
    # Notification management
    path('notifications/', manage_notifications, name='manage_notifications'),
    path('notifications/create/', create_notification, name='create_notification'),
    path('notifications/<int:notification_id>/toggle/', toggle_notification, name='toggle_notification'),
    path('notifications/<int:notification_id>/delete/', delete_notification, name='delete_notification'),
    path('notifications/schedule-maintenance/', schedule_maintenance, name='schedule_maintenance'),
]
