import posthog
import traceback
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from os import environ

User = get_user_model()


class PostHogErrorTrackingMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if not environ.get('POSTHOG_API_KEY'):
            return None
            
        user_id = 'anonymous'
        user_data = {}
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
            user_data = {
                'email': getattr(request.user, 'email', ''),
                'username': getattr(request.user, 'username', ''),
            }
        
        error_data = {
            'error_type': type(exception).__name__,
            'error_message': str(exception),
            'error_traceback': traceback.format_exc(),
            'request_method': request.method,
            'request_path': request.path,
            'request_full_path': request.get_full_path(),
            'request_host': request.get_host(),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': self.get_client_ip(request),
            '$process_person_profile': True,
            **user_data
        }
        
        try:
            posthog.capture(
                user_id,
                'server_error',
                properties=error_data
            )
        except Exception as e:
            pass
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip