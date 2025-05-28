import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import StatusNotification, DatabaseStatus

logger = logging.getLogger(__name__)

# Time constants (for scheduling)
HOUR = 3600
DAY = 86400

User = get_user_model()

class NotificationManager:
    """Manages the creation, distribution, and tracking of user notifications for the database refresh process."""
    
    @classmethod
    def create_maintenance_notification(cls, title, message, start_time, end_time, notification_type='warning'):
        """Create a system-wide maintenance notification for the database refresh.
        
        Args:
            title: The notification title
            message: The notification message content
            start_time: When the maintenance begins (datetime)
            end_time: Expected end time for maintenance (datetime)
            notification_type: Bootstrap alert type (warning, danger, info, primary)
            
        Returns:
            The created StatusNotification object
        """
        notification = StatusNotification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            is_active=True,
            start_display=timezone.now(),  # Display immediately
            end_display=end_time + timedelta(days=1),  # Show until a day after completion
            display_order=10,  # Higher priority
            dismissible=False,  # Cannot be dismissed during maintenance
            display_on_all_pages=True
        )
        
        # Update database status with maintenance message
        status, created = DatabaseStatus.objects.get_or_create(pk=1)
        status.maintenance_message = message
        status.save()
        
        logger.info(f"Created maintenance notification: {title}")
        return notification
    
    @classmethod
    def send_email_notification(cls, title, message, recipients=None, include_all_users=False):
        """Send email notifications to users about the database refresh.
        
        Args:
            title: Email subject
            message: Email body text
            recipients: List of email addresses or User objects
            include_all_users: If True, send to all active users
            
        Returns:
            Number of emails sent
        """
        if not recipients:
            recipients = []
            
        # Get all active users if requested
        if include_all_users:
            user_emails = User.objects.filter(is_active=True).values_list('email', flat=True)
            recipients.extend(user_emails)
        
        # Convert User objects to email addresses if needed
        processed_recipients = []
        for recipient in recipients:
            if hasattr(recipient, 'email'):
                processed_recipients.append(recipient.email)
            else:
                processed_recipients.append(recipient)
        
        # Remove duplicates and empty emails
        processed_recipients = list(set([email for email in processed_recipients if email]))
        
        if not processed_recipients:
            logger.warning("No valid recipients for email notification")
            return 0
        
        # Get status URL for email
        status_url = settings.SITE_URL + reverse('refresh_status:status')
        
        # Create HTML version of email
        html_message = render_to_string('refresh_status/email_notification.html', {
            'title': title,
            'message': message,
            'status_url': status_url,
            'site_name': settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Concrete Mix Database'
        })
        
        # Send email
        try:
            subject = f"{settings.EMAIL_SUBJECT_PREFIX if hasattr(settings, 'EMAIL_SUBJECT_PREFIX') else ''}Concrete Mix Database: {title}"
            from_email = settings.DEFAULT_FROM_EMAIL
            
            # Use EmailMultiAlternatives for HTML emails
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=processed_recipients
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Sent email notification '{title}' to {len(processed_recipients)} recipients")
            return len(processed_recipients)
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return 0
    
    @classmethod
    def schedule_refresh_notifications(cls, start_time, estimated_duration):
        """Schedule all notifications for a database refresh.
        
        Args:
            start_time: When the refresh will begin (datetime)
            estimated_duration: Estimated duration in hours (float)
            
        Returns:
            Dictionary with scheduled notification details
        """
        end_time = start_time + timedelta(hours=estimated_duration)
        
        # Format times for messages
        start_str = start_time.strftime("%A, %B %d at %H:%M")
        end_str = end_time.strftime("%A, %B %d at %H:%M")
        duration_str = f"{estimated_duration:.1f} hours" if estimated_duration < 24 else f"{estimated_duration/24:.1f} days"
        
        # Create pre-maintenance notification (displayed 3 days before)
        advance_message = f"""The Concrete Mix Database will undergo scheduled maintenance beginning {start_str}. 
        During this time, the database will be refreshed to resolve data consistency issues.
        
        Expected duration: {duration_str}
        During maintenance: Read-only access to existing data
        
        Please save any work in progress before the maintenance window begins."""
        
        advance_notification = StatusNotification.objects.create(
            title="Upcoming Database Maintenance",
            message=advance_message,
            notification_type="info",
            is_active=True,
            start_display=start_time - timedelta(days=3),  # 3 days before
            end_display=start_time,  # Until maintenance begins
            display_order=5,
            dismissible=True,
            display_on_all_pages=True
        )
        
        # Create during-maintenance notification
        during_message = f"""Database maintenance is currently in progress. 
        
        Started: {start_str}
        Expected completion: {end_str}
        
        The system is in read-only mode. You can view data, but cannot make changes 
        until the maintenance is complete.
        
        See the <a href='{reverse('refresh_status:status')}'>status page</a> for real-time updates."""
        
        during_notification = StatusNotification.objects.create(
            title="Database Maintenance In Progress",
            message=during_message,
            notification_type="warning",
            is_active=True,
            start_display=start_time,  # From when maintenance begins
            end_display=end_time + timedelta(hours=6),  # Until 6 hours after expected completion
            display_order=10,  # Higher priority
            dismissible=False,  # Cannot be dismissed during maintenance
            display_on_all_pages=True
        )
        
        # Send initial email to all users
        cls.send_email_notification(
            title="Upcoming Database Maintenance",
            message=advance_message,
            include_all_users=True
        )
        
        logger.info(f"Scheduled all notifications for database refresh starting {start_str}")
        
        return {
            "advance_notification": advance_notification.id,
            "during_notification": during_notification.id,
            "start_time": start_time,
            "end_time": end_time
        }
    
    @classmethod
    def update_maintenance_status(cls, status, progress_percentage=None, current_phase=None, current_step=None):
        """Update the maintenance status and corresponding notifications.
        
        Args:
            status: One of the DatabaseStatus status constants
            progress_percentage: Optional progress percentage (0-100)
            current_phase: Current phase name
            current_step: Current step within the phase
            
        Returns:
            The updated DatabaseStatus object
        """
        db_status, created = DatabaseStatus.objects.get_or_create(pk=1)
        db_status.status = status
        
        if progress_percentage is not None:
            db_status.progress_percentage = progress_percentage
            
        if current_phase:
            db_status.current_phase = current_phase
            
        if current_step:
            db_status.current_step = current_step
        
        db_status.save()
        
        # Update notifications based on status
        if status == DatabaseStatus.COMPLETED:
            # Create completion notification
            completion_message = f"""The database refresh has been successfully completed.
            
            All data has been refreshed and normal database operations have been restored.
            
            If you encounter any issues, please contact the database administrator."""
            
            completion_notification = StatusNotification.objects.create(
                title="Database Refresh Completed",
                message=completion_message,
                notification_type="success",
                is_active=True,
                start_display=timezone.now(),
                end_display=timezone.now() + timedelta(days=2),  # Show for 2 days
                display_order=8,
                dismissible=True,
                display_on_all_pages=True
            )
            
            # Set all warnings to inactive
            StatusNotification.objects.filter(notification_type="warning").update(is_active=False)
            
            # Clear maintenance message
            db_status.maintenance_message = ""
            db_status.save()
            
            # Send completion email
            cls.send_email_notification(
                title="Database Refresh Completed",
                message=completion_message,
                include_all_users=True
            )
        
        logger.info(f"Updated maintenance status to: {status}")
        return db_status
