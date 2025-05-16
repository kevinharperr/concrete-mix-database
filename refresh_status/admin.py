from django.contrib import admin
from .models import DatabaseStatus, StatusNotification, RefreshLogEntry

@admin.register(DatabaseStatus)
class DatabaseStatusAdmin(admin.ModelAdmin):
    list_display = ('status', 'read_only_mode', 'current_phase', 'progress_percentage', 'last_updated')
    readonly_fields = ('last_updated',)
    fieldsets = (
        ('Status Information', {
            'fields': ('status', 'read_only_mode', 'current_phase', 'current_step', 'progress_percentage')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'estimated_completion', 'last_updated')
        }),
        ('Messages', {
            'fields': ('maintenance_message', 'error_message')
        }),
    )

@admin.register(StatusNotification)
class StatusNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'is_active', 'display_order', 'start_display', 'end_display')
    list_filter = ('notification_type', 'is_active')
    search_fields = ('title', 'message')
    fieldsets = (
        ('Content', {
            'fields': ('title', 'message', 'notification_type')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'display_order', 'dismissible', 'start_display', 'end_display')
        }),
        ('Page Targeting', {
            'fields': ('display_on_all_pages', 'specific_pages'),
            'description': 'Specify which pages should show this notification'
        }),
    )

@admin.register(RefreshLogEntry)
class RefreshLogEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'phase', 'step', 'status', 'is_error')
    list_filter = ('phase', 'status', 'is_error')
    search_fields = ('message', 'phase', 'step')
    readonly_fields = ('timestamp',)
    fieldsets = (
        ('Log Information', {
            'fields': ('timestamp', 'phase', 'step', 'status', 'is_error')
        }),
        ('Details', {
            'fields': ('message', 'details')
        }),
    )
