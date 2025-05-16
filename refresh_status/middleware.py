"""
Middleware for enforcing read-only mode during database refresh operations.

This middleware checks the current database status and blocks write operations
(POST, PUT, DELETE requests) when read-only mode is enabled.
"""
import json
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin

from .models import DatabaseStatus

class ReadOnlyModeMiddleware(MiddlewareMixin):
    """
    Middleware to enforce read-only mode based on DatabaseStatus.
    
    When read_only_mode is 'on', this middleware will:
    - Block all POST, PUT, DELETE requests except for specific exempt URLs
    - Allow GET requests to continue normally
    - Redirect blocked requests with an appropriate message
    """
    
    # URLs that should be accessible even in read-only mode
    EXEMPT_URLS = [
        '/admin/login/',                      # Admin login
        '/accounts/login/',                   # User login
        '/accounts/logout/',                  # User logout
        '/status/api/update/',                # Status updates
        '/status/admin/',                     # Admin status page
        '/admin/refresh_status/',             # Admin app for refresh status
        '/admin/jsi18n/',                     # Required for admin
    ]
    
    # Additional exempt URL prefixes
    EXEMPT_URL_PREFIXES = [
        '/admin/refresh_status/',             # All refresh status admin URLs
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        """Process the request and enforce read-only mode if active."""
        # Skip middleware if request method is safe (GET, HEAD, OPTIONS)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return self.get_response(request)
        
        # Check current URL against exempt URLs
        path = request.path
        
        # Allow exempt URLs and prefixes even in read-only mode
        if path in self.EXEMPT_URLS or any(path.startswith(prefix) for prefix in self.EXEMPT_URL_PREFIXES):
            return self.get_response(request)
            
        # Check if read-only mode is active
        try:
            status = DatabaseStatus.objects.latest('last_updated')
            is_read_only = status.read_only_mode == DatabaseStatus.READ_ONLY_ON
        except DatabaseStatus.DoesNotExist:
            # If no status exists, default to allowing writes
            is_read_only = False
        
        # If read-only mode is active, block the request
        if is_read_only:
            return self.handle_blocked_request(request)
            
        # Otherwise, allow the request to proceed
        return self.get_response(request)
    
    def handle_blocked_request(self, request):
        """Handle a request that is blocked due to read-only mode."""
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            # Return JSON response for AJAX requests
            return JsonResponse({
                'success': False,
                'error': 'The database is currently in read-only mode due to maintenance. '
                         'Please try again later.'
            }, status=423)  # HTTP 423 Locked
        else:
            # For normal requests, add a message and redirect
            messages.error(
                request,
                'The database is currently in read-only mode due to maintenance. '
                'Modifications are temporarily disabled.'
            )
            # Redirect to the status page or the previous page
            redirect_url = request.META.get('HTTP_REFERER')
            if not redirect_url:
                redirect_url = reverse('refresh_status:status')
            
            return HttpResponseRedirect(redirect_url)
