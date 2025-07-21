import os
from django.utils.translation import gettext_lazy as _


def add_user_tags(request):
    """
    Add user tags for PostHog middleware tracking
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Dict[str, Any]: Dictionary of tags to add to PostHog events
    """
    tags = {}
    if hasattr(request, 'user') and request.user.is_authenticated:
        tags['user_id'] = str(request.user.id)
        tags['email'] = getattr(request.user, 'email', '')
        tags['username'] = getattr(request.user, 'username', '')
        tags['is_staff'] = getattr(request.user, 'is_staff', False)
        tags['is_superuser'] = getattr(request.user, 'is_superuser', False)
        
        # Add any custom user fields if they exist
        if hasattr(request.user, 'first_name'):
            tags['first_name'] = request.user.first_name
        if hasattr(request.user, 'last_name'):
            tags['last_name'] = request.user.last_name
        if hasattr(request.user, 'date_joined'):
            tags['date_joined'] = request.user.date_joined.isoformat()
    else:
        tags['user_id'] = 'anonymous'
        tags['is_authenticated'] = False
    
    return tags


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
    posthog_project_id = os.environ.get('POSTHOG_PROJECT_ID', '')
    
    if posthog_api_key:
        # Add PostHog Django middleware for automatic context and exception tracking
        main_settings['MIDDLEWARE'] += [
            'posthog.integrations.django.PosthogContextMiddleware',
        ]
        
        # PostHog middleware settings
        main_settings['POSTHOG_MW_CAPTURE_EXCEPTIONS'] = True  # Capture exceptions automatically
        main_settings['POSTHOG_MW_EXTRA_TAGS'] = add_user_tags  # Add custom user tags
        
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
                "link": f"{posthog_host}/project/{posthog_project_id}/errors" if posthog_api_key and posthog_project_id else "#",
                "permission": lambda request: request.user.is_staff,
            },
            {
                "title": _("Analytics Dashboard"),
                "icon": "dashboard",
                "link": f"{posthog_host}/project/{posthog_project_id}/dashboard" if posthog_api_key and posthog_project_id else "#", 
                "permission": lambda request: request.user.is_staff,
            },
        ]
    })
    
    return main_settings