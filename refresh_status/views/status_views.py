"""Views for displaying database refresh status."""
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.utils import timezone

from refresh_status.models import DatabaseStatus, StatusNotification, RefreshLogEntry

class StatusPageView(TemplateView):
    """Public-facing status page showing current database refresh status."""
    template_name = 'refresh_status/status_page.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current status or create if it doesn't exist
        try:
            status = DatabaseStatus.objects.latest('last_updated')
        except DatabaseStatus.DoesNotExist:
            status = DatabaseStatus.objects.create()
        
        # Get active notifications
        notifications = StatusNotification.objects.filter(is_active=True)
        active_notifications = [n for n in notifications if n.is_displayed()]
        
        # Get recent log entries (limit to 20 most recent)
        log_entries = RefreshLogEntry.objects.all()[:20]
        
        context.update({
            'status': status,
            'notifications': active_notifications,
            'log_entries': log_entries,
        })
        
        return context

@method_decorator(staff_member_required, name='dispatch')
class AdminStatusView(TemplateView):
    """Admin-only view for managing database status and notifications."""
    template_name = 'refresh_status/admin_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current status
        try:
            status = DatabaseStatus.objects.latest('last_updated')
        except DatabaseStatus.DoesNotExist:
            status = DatabaseStatus.objects.create()
        
        # Get all notifications
        notifications = StatusNotification.objects.all()
        
        # Get all log entries with pagination (30 per page)
        log_entries = RefreshLogEntry.objects.all()[:30]
        
        context.update({
            'status': status,
            'notifications': notifications,
            'log_entries': log_entries,
        })
        
        return context

@staff_member_required
def update_status(request):
    """AJAX endpoint for updating database status."""
    if request.method == 'POST':
        try:
            status = DatabaseStatus.objects.latest('last_updated')
        except DatabaseStatus.DoesNotExist:
            status = DatabaseStatus()
            
        # Check for read-only mode changes to specially log them
        read_only_changed = False
        old_read_only_mode = status.read_only_mode if hasattr(status, 'read_only_mode') else 'off'
        
        # Update fields based on POST data
        if 'status' in request.POST:
            status.status = request.POST.get('status')
        if 'read_only_mode' in request.POST:
            new_mode = request.POST.get('read_only_mode')
            if new_mode != old_read_only_mode:
                read_only_changed = True
                status.read_only_mode = new_mode
        if 'current_phase' in request.POST:
            status.current_phase = request.POST.get('current_phase')
        if 'current_step' in request.POST:
            status.current_step = request.POST.get('current_step')
        if 'progress_percentage' in request.POST:
            status.progress_percentage = int(request.POST.get('progress_percentage'))
        if 'maintenance_message' in request.POST:
            status.maintenance_message = request.POST.get('maintenance_message')
            
        status.save()
        
        # Always log read-only mode changes
        if read_only_changed:
            mode_message = "Read-only mode enabled" if status.read_only_mode == 'on' else "Read-only mode disabled"
            RefreshLogEntry.objects.create(
                phase=status.current_phase,
                step=status.current_step,
                status='read_only_mode_change',
                message=f"{mode_message} by {request.user.username}",
                is_error=False,
                details={
                    'previous': old_read_only_mode,
                    'current': status.read_only_mode,
                    'changed_by': request.user.username,
                }
            )
        
        # Log the status update if requested
        elif request.POST.get('log_entry', 'false').lower() == 'true':
            RefreshLogEntry.objects.create(
                phase=status.current_phase,
                step=status.current_step,
                status=status.status,
                message=request.POST.get('message', f"Status updated to {status.get_status_display()}"),
                is_error=(status.status == DatabaseStatus.ERROR),
            )
            
        return JsonResponse({
            'success': True,
            'status': status.status,
            'read_only_mode': status.read_only_mode
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

def get_status_json(request):
    """AJAX endpoint for retrieving current database status as JSON."""
    try:
        status = DatabaseStatus.objects.latest('last_updated')
        
        data = {
            'success': True,
            'status': status.status,
            'status_display': status.get_status_display(),
            'read_only_mode': status.read_only_mode,
            'current_phase': status.current_phase,
            'current_step': status.current_step,
            'progress_percentage': status.progress_percentage,
            'last_updated': status.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
            'maintenance_message': status.maintenance_message,
        }
        
        # Add timing information if available
        if status.start_time:
            data['start_time'] = status.start_time.strftime('%Y-%m-%d %H:%M:%S')
        if status.end_time:
            data['end_time'] = status.end_time.strftime('%Y-%m-%d %H:%M:%S')
        if status.estimated_completion:
            data['estimated_completion'] = status.estimated_completion.strftime('%Y-%m-%d %H:%M:%S')
            
        return JsonResponse(data)
    except DatabaseStatus.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No status information available'
        })
