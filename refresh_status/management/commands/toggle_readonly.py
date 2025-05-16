#!/usr/bin/env python
"""
Management command to toggle read-only mode for the Concrete Mix Database.
This command allows administrators to enable or disable read-only mode
from the command line or in scripts.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from refresh_status.models import DatabaseStatus, RefreshLogEntry

class Command(BaseCommand):
    help = 'Toggle read-only mode for the database application'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--on',
            action='store_true',
            help='Enable read-only mode',
        )
        
        parser.add_argument(
            '--off',
            action='store_true',
            help='Disable read-only mode',
        )
        
        parser.add_argument(
            '--message',
            type=str,
            help='Message to display to users when read-only mode is enabled',
        )
        
        parser.add_argument(
            '--phase',
            type=str,
            help='Current phase of the database refresh process',
        )
        
        parser.add_argument(
            '--step',
            type=str,
            help='Current step within the phase',
        )
    
    def handle(self, *args, **options):
        # Check for conflicting arguments
        if options['on'] and options['off']:
            raise CommandError("Cannot specify both --on and --off")
        
        if not options['on'] and not options['off']:
            # If no arguments provided, show current status
            self._show_current_status()
            return
        
        try:
            # Get or create status object
            try:
                status = DatabaseStatus.objects.latest('last_updated')
            except DatabaseStatus.DoesNotExist:
                status = DatabaseStatus()
            
            # Process the command
            if options['on']:
                status.read_only_mode = DatabaseStatus.READ_ONLY_ON
                action_message = 'Enabled read-only mode'
            else:
                status.read_only_mode = DatabaseStatus.READ_ONLY_OFF
                action_message = 'Disabled read-only mode'
            
            # Update additional fields if provided
            if options['phase']:
                status.current_phase = options['phase']
            
            if options['step']:
                status.current_step = options['step']
            
            if options['message']:
                status.maintenance_message = options['message']
            
            # Save status
            status.last_updated = timezone.now()
            status.save()
            
            # Create log entry
            RefreshLogEntry.objects.create(
                phase=status.current_phase,
                step=status.current_step,
                status='read_only_mode_change',
                message=action_message,
            )
            
            # Output success message
            self.stdout.write(self.style.SUCCESS(action_message))
            
        except Exception as e:
            raise CommandError(f"Error toggling read-only mode: {str(e)}")
    
    def _show_current_status(self):
        """Display the current read-only status."""
        try:
            status = DatabaseStatus.objects.latest('last_updated')
            is_readonly = status.read_only_mode == DatabaseStatus.READ_ONLY_ON
            
            if is_readonly:
                self.stdout.write(self.style.WARNING('Read-only mode is currently ENABLED'))
                self.stdout.write(f"Phase: {status.current_phase}")
                self.stdout.write(f"Step: {status.current_step}")
                self.stdout.write(f"Last updated: {status.last_updated}")
                if status.maintenance_message:
                    self.stdout.write(f"Message: {status.maintenance_message}")
            else:
                self.stdout.write(self.style.SUCCESS('Read-only mode is currently DISABLED'))
                
        except DatabaseStatus.DoesNotExist:
            self.stdout.write(self.style.SUCCESS('Read-only mode is currently DISABLED (no status record)'))
