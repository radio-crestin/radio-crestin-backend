import sys
import traceback
import posthog
from django.http import Http404
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.views.defaults import (
    bad_request, permission_denied, page_not_found, server_error
)
from django.contrib.auth import get_user_model
from os import environ

User = get_user_model()


def get_user_info(request):
    """Extract user information for PostHog tracking"""
    user_id = 'anonymous'
    user_data = {}
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        user_id = str(request.user.id)
        user_data = {
            'email': getattr(request.user, 'email', ''),
            'username': getattr(request.user, 'username', ''),
            'is_staff': getattr(request.user, 'is_staff', False),
            'is_superuser': getattr(request.user, 'is_superuser', False),
        }
    
    return user_id, user_data


def get_request_info(request):
    """Extract request information for PostHog tracking"""
    return {
        'request_method': request.method,
        'request_path': request.path,
        'request_full_path': request.get_full_path(),
        'request_host': request.get_host(),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'ip_address': get_client_ip(request),
        'referer': request.META.get('HTTP_REFERER', ''),
        'content_type': request.META.get('CONTENT_TYPE', ''),
    }


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def track_error(request, error_type, error_message, status_code, exception=None):
    """Track error to PostHog"""
    if not environ.get('POSTHOG_API_KEY'):
        return
    
    user_id, user_data = get_user_info(request)
    request_data = get_request_info(request)
    
    error_data = {
        'error_type': error_type,
        'error_message': error_message,
        'status_code': status_code,
        '$process_person_profile': True,
        **user_data,
        **request_data
    }
    
    if exception:
        error_data['error_traceback'] = traceback.format_exc()
    
    try:
        posthog.capture(
            user_id,
            'http_error',
            properties=error_data
        )
    except Exception:
        # Silently fail if PostHog tracking fails
        pass


def custom_404_handler(request, exception, template_name='404.html'):
    """Custom 404 error handler with PostHog tracking"""
    track_error(
        request,
        error_type='Http404',
        error_message=str(exception) if exception else 'Page not found',
        status_code=404,
        exception=exception
    )
    return page_not_found(request, exception, template_name)


def custom_500_handler(request, template_name='500.html'):
    """Custom 500 error handler with PostHog tracking"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    error_message = str(exc_value) if exc_value else 'Internal server error'
    error_type = exc_type.__name__ if exc_type else 'UnknownError'
    
    track_error(
        request,
        error_type=error_type,
        error_message=error_message,
        status_code=500,
        exception=exc_value
    )
    return server_error(request, template_name)


def custom_403_handler(request, exception, template_name='403.html'):
    """Custom 403 error handler with PostHog tracking"""
    track_error(
        request,
        error_type='PermissionDenied',
        error_message=str(exception) if exception else 'Permission denied',
        status_code=403,
        exception=exception
    )
    return permission_denied(request, exception, template_name)


def custom_400_handler(request, exception, template_name='400.html'):
    """Custom 400 error handler with PostHog tracking"""
    track_error(
        request,
        error_type='BadRequest',
        error_message=str(exception) if exception else 'Bad request',
        status_code=400,
        exception=exception
    )
    return bad_request(request, exception, template_name)


def register_global_error_handlers():
    """Register global error handlers for Django"""
    from django.conf import settings
    
    # Only register if PostHog is configured
    if not environ.get('POSTHOG_API_KEY'):
        return
    
    # Set custom error handlers in Django settings
    settings.handler404 = 'superapp.apps.posthog_error_tracking.error_handlers.custom_404_handler'
    settings.handler500 = 'superapp.apps.posthog_error_tracking.error_handlers.custom_500_handler'
    settings.handler403 = 'superapp.apps.posthog_error_tracking.error_handlers.custom_403_handler'
    settings.handler400 = 'superapp.apps.posthog_error_tracking.error_handlers.custom_400_handler'