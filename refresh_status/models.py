from django.db import models
from django.utils import timezone

class DatabaseStatus(models.Model):
    """Tracks the current status of the database refresh process."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    ERROR = 'error'
    PAUSED = 'paused'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (ERROR, 'Error'),
        (PAUSED, 'Paused'),
    ]
    
    READ_ONLY_OFF = 'off'
    READ_ONLY_ON = 'on'
    
    READ_ONLY_CHOICES = [
        (READ_ONLY_OFF, 'Off'),
        (READ_ONLY_ON, 'On'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    read_only_mode = models.CharField(max_length=10, choices=READ_ONLY_CHOICES, default=READ_ONLY_OFF)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    current_phase = models.CharField(max_length=100, blank=True)
    current_step = models.CharField(max_length=100, blank=True)
    progress_percentage = models.IntegerField(default=0)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)
    maintenance_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Database Statuses"
    
    def save(self, *args, **kwargs):
        if self.status == self.IN_PROGRESS and not self.start_time:
            self.start_time = timezone.now()
        elif self.status == self.COMPLETED and not self.end_time:
            self.end_time = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Database Status: {self.get_status_display()}"

class StatusNotification(models.Model):
    """Manages notifications displayed to users during the refresh process."""
    INFO = 'info'
    WARNING = 'warning'
    DANGER = 'danger'
    PRIMARY = 'primary'
    
    NOTIFICATION_TYPES = [
        (INFO, 'Info'),
        (WARNING, 'Warning'),
        (DANGER, 'Danger'),
        (PRIMARY, 'Primary'),
    ]
    
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default=INFO)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_display = models.DateTimeField(default=timezone.now)
    end_display = models.DateTimeField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    dismissible = models.BooleanField(default=True)
    display_on_all_pages = models.BooleanField(default=True)
    specific_pages = models.CharField(max_length=255, blank=True, help_text="Comma-separated list of URL paths where this notification should appear")
    
    class Meta:
        ordering = ['display_order', '-created_at']
    
    def __str__(self):
        return self.title
    
    def is_displayed(self):
        """Check if the notification should currently be displayed."""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_display:
            return False
        if self.end_display and now > self.end_display:
            return False
        return True

class RefreshLogEntry(models.Model):
    """Logs detailed information about each step in the refresh process."""
    timestamp = models.DateTimeField(auto_now_add=True)
    phase = models.CharField(max_length=100)
    step = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    message = models.TextField()
    is_error = models.BooleanField(default=False)
    details = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Refresh Log Entries"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.phase} - {self.step}"
