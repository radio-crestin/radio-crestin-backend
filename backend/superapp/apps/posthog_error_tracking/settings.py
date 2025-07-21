import os
from django.utils.translation import gettext_lazy as _


def extend_superapp_settings(main_settings):
    """
    Extend main Django settings with PostHog error tracking configuration
    """
    
    # Add the app to INSTALLED_APPS
    main_settings['INSTALLED_APPS'] = [
        'superapp.apps.posthog_error_tracking',
    ] + main_settings['INSTALLED_APPS']
    
    # PostHog configuration
    posthog_api_key = os.environ.get('POSTHOG_API_KEY', '')
    posthog_host = os.environ.get('POSTHOG_HOST', 'https://eu.i.posthog.com')
    
    if posthog_api_key:
        # Add PostHog Django middleware for automatic context and exception tracking
        main_settings['MIDDLEWARE'] += [
            'posthog.integrations.django.PosthogContextMiddleware',
        ]
        
        # PostHog middleware settings
        main_settings['POSTHOG_MW_CAPTURE_EXCEPTIONS'] = True  # Capture exceptions automatically
        
        # PostHog configuration
        main_settings['POSTHOG_PROJECT_API_KEY'] = posthog_api_key
        main_settings['POSTHOG_HOST'] = posthog_host
        
        # Enable automatic session and user tracking
        main_settings['POSTHOG_MW_ENABLE_SESSION_TRACKING'] = True
        main_settings['POSTHOG_MW_ENABLE_USER_TRACKING'] = True
    
    # Add admin sidebar navigation for PostHog error tracking
    main_settings.setdefault('UNFOLD', {}).setdefault('SIDEBAR', {}).setdefault('navigation', []).append({
        "title": _("PostHog Analytics"),
        "icon": "analytics",
        "permission": lambda request: request.user.is_staff,
        "items": [
            {
                "title": _("Error Tracking"),
                "icon": "bug_report",
                "link": f"{posthog_host}/project/1/errors" if posthog_api_key else "#",
                "permission": lambda request: request.user.is_staff,
            },
            {
                "title": _("Analytics Dashboard"),
                "icon": "dashboard",
                "link": f"{posthog_host}/project/1/dashboard" if posthog_api_key else "#", 
                "permission": lambda request: request.user.is_staff,
            },
        ]
    })
    
    return main_settings