from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.http import JsonResponse
from ..models import StatusNotification, DatabaseStatus
from ..notifications import NotificationManager


def is_staff(user):
    return user.is_staff


# Temporarily removed authentication for development
# @login_required
# @user_passes_test(is_staff)
def manage_notifications(request):
    """Admin interface for managing refresh notifications."""
    notifications = StatusNotification.objects.all().order_by('-is_active', 'display_order', '-created_at')
    
    # Get database status
    db_status, _ = DatabaseStatus.objects.get_or_create(pk=1)
    
    context = {
        'notifications': notifications,
        'db_status': db_status,
        'notification_types': StatusNotification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'refresh_status/manage_notifications.html', context)


# Temporarily removed authentication for development
# @login_required
# @user_passes_test(is_staff)
def create_notification(request):
    """Create a new notification."""
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        dismissible = request.POST.get('dismissible') == 'on'
        display_on_all_pages = request.POST.get('display_on_all_pages') == 'on'
        specific_pages = request.POST.get('specific_pages', '')
        # Handle empty display_order value safely
        display_order_value = request.POST.get('display_order', '')
        display_order = int(display_order_value) if display_order_value.strip() else 0
        
        # Handle duration
        # Handle empty duration_days value safely
        duration_days_value = request.POST.get('duration_days', '')
        duration_days = int(duration_days_value) if duration_days_value.strip() else 1
        start_display = timezone.now()
        end_display = start_display + timedelta(days=duration_days)
        
        notification = StatusNotification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            is_active=True,
            start_display=start_display,
            end_display=end_display,
            display_order=display_order,
            dismissible=dismissible,
            display_on_all_pages=display_on_all_pages,
            specific_pages=specific_pages
        )
        
        # Send email if requested
        if request.POST.get('send_email') == 'on':
            recipients = []
            if request.POST.get('email_all_users') == 'on':
                include_all_users = True
            else:
                include_all_users = False
                
            NotificationManager.send_email_notification(
                title=title,
                message=message,
                recipients=recipients,
                include_all_users=include_all_users
            )
            messages.success(request, "Notification created and email sent successfully.")
        else:
            messages.success(request, "Notification created successfully.")
            
        return redirect('refresh_status:manage_notifications')
    
    return redirect('refresh_status:manage_notifications')


# Temporarily removed authentication for development
# @login_required
# @user_passes_test(is_staff)
def toggle_notification(request, notification_id):
    """Toggle a notification's active status."""
    notification = get_object_or_404(StatusNotification, id=notification_id)
    notification.is_active = not notification.is_active
    notification.save()
    
    return JsonResponse({
        'success': True,
        'is_active': notification.is_active
    })


# Temporarily removed authentication for development
# @login_required
# @user_passes_test(is_staff)
def delete_notification(request, notification_id):
    """Delete a notification."""
    notification = get_object_or_404(StatusNotification, id=notification_id)
    notification.delete()
    messages.success(request, "Notification deleted successfully.")
    
    return redirect('refresh_status:manage_notifications')


# Temporarily removed authentication for development
# @login_required
# @user_passes_test(is_staff)
def schedule_maintenance(request):
    """Schedule a maintenance window with all necessary notifications."""
    if request.method == 'POST':
        try:
            # Parse maintenance window details
            start_date = request.POST.get('start_date')
            start_time = request.POST.get('start_time')
            # Handle empty duration_hours value safely
            duration_hours_value = request.POST.get('duration_hours', '')
            duration_hours = float(duration_hours_value) if duration_hours_value.strip() else 2.0
            
            # Combine date and time
            start_datetime_str = f"{start_date} {start_time}"
            start_datetime = timezone.datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
            # Make timezone-aware
            start_datetime = timezone.make_aware(start_datetime)
            
            # Schedule all notifications
            result = NotificationManager.schedule_refresh_notifications(
                start_time=start_datetime,
                estimated_duration=duration_hours
            )
            
            # Update database status
            db_status, _ = DatabaseStatus.objects.get_or_create(pk=1)
            db_status.estimated_completion = start_datetime + timedelta(hours=duration_hours)
            db_status.save()
            
            messages.success(request, "Maintenance window scheduled successfully.")
            return redirect('refresh_status:manage_notifications')
            
        except Exception as e:
            messages.error(request, f"Error scheduling maintenance: {str(e)}")
            return redirect('refresh_status:manage_notifications')
    
    return redirect('refresh_status:manage_notifications')
