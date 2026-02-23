from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy


def extend_superapp_settings(main_settings):
    """Extend main SuperApp settings with radio_crestin app configuration."""

    # Add this app to INSTALLED_APPS
    main_settings['INSTALLED_APPS'] += ['superapp.apps.radio_crestin']
    
    # Add custom subdomain routing middleware (must be early in the middleware stack)
    middleware_class = 'superapp.apps.radio_crestin.middleware.SubdomainRoutingMiddleware'
    if middleware_class not in main_settings['MIDDLEWARE']:
        # Insert after SecurityMiddleware but before other middlewares
        try:
            security_index = main_settings['MIDDLEWARE'].index('django.middleware.security.SecurityMiddleware')
            main_settings['MIDDLEWARE'].insert(security_index + 1, middleware_class)
        except ValueError:
            # If SecurityMiddleware not found, add at the beginning
            main_settings['MIDDLEWARE'].insert(0, middleware_class)

    # Add app-specific navigation to the admin sidebar
    main_settings['UNFOLD']['SIDEBAR']['navigation'] += [
        {
            "title": _("Radio Crestin"),
            "icon": "radio",
            "items": [
                {
                    "title": lambda request: _("Radio Stations"),
                    "icon": "radio",
                    "link": reverse_lazy("admin:radio_crestin_stations_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stations"),
                },
                {
                    "title": lambda request: _("Station Groups"),
                    "icon": "folder",
                    "link": reverse_lazy("admin:radio_crestin_stationgroups_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationgroups"),
                },
                {
                    "title": lambda request: _("Artists"),
                    "icon": "person",
                    "link": reverse_lazy("admin:radio_crestin_artists_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_artists"),
                },
                {
                    "title": lambda request: _("Songs"),
                    "icon": "music_note",
                    "link": reverse_lazy("admin:radio_crestin_songs_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_songs"),
                },
                {
                    "title": lambda request: _("Now Playing"),
                    "icon": "play_circle",
                    "link": reverse_lazy("admin:radio_crestin_stationsnowplaying_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationsnowplaying"),
                },
                {
                    "title": lambda request: _("Now Playing History"),
                    "icon": "history",
                    "link": reverse_lazy("admin:radio_crestin_stationsnowplayinghistory_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationsnowplayinghistory"),
                },
                {
                    "title": lambda request: _("Station Uptime"),
                    "icon": "trending_up",
                    "link": reverse_lazy("admin:radio_crestin_stationsuptime_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationsuptime"),
                },
                {
                    "title": lambda request: _("Posts"),
                    "icon": "article",
                    "link": reverse_lazy("admin:radio_crestin_posts_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_posts"),
                },
                {
                    "title": lambda request: _("Station Streams"),
                    "icon": "stream",
                    "link": reverse_lazy("admin:radio_crestin_stationstreams_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationstreams"),
                },
                {
                    "title": lambda request: _("Metadata Categories"),
                    "icon": "category",
                    "link": reverse_lazy("admin:radio_crestin_stationmetadatafetchcategories_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationmetadatafetchcategories"),
                },
                {
                    "title": lambda request: _("Station to Group"),
                    "icon": "link",
                    "link": reverse_lazy("admin:radio_crestin_stationtostationgroup_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationtostationgroup"),
                },
                {
                    "title": lambda request: _("Metadata Fetch"),
                    "icon": "sync",
                    "link": reverse_lazy("admin:radio_crestin_stationsmetadatafetch_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_stationsmetadatafetch"),
                },
                {
                    "title": lambda request: _("Listening Sessions"),
                    "icon": "headphones",
                    "link": reverse_lazy("admin:radio_crestin_listeningsessions_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_listeningsessions"),
                },
                {
                    "title": lambda request: _("Reviews"),
                    "icon": "star",
                    "link": reverse_lazy("admin:radio_crestin_reviews_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_reviews"),
                },
                {
                    "title": lambda request: _("App Users"),
                    "icon": "people",
                    "link": reverse_lazy("admin:radio_crestin_appusers_changelist"),
                    "permission": lambda request: request.user.has_perm("radio_crestin.view_appusers"),
                },
            ]
        },
    ]

    # Configure Celery Beat schedules for cleanup tasks
    import os
    setup_scheduled_tasks = os.getenv('SETUP_SCHEDULED_TASKS', 'true').lower() == 'true'
    
    if setup_scheduled_tasks:
        from celery.schedules import crontab

        # Initialize CELERY_BEAT_SCHEDULE if it doesn't exist
        if 'CELERY_BEAT_SCHEDULE' not in main_settings:
            main_settings['CELERY_BEAT_SCHEDULE'] = {}

        # Add radio_crestin cleanup tasks
        main_settings['CELERY_BEAT_SCHEDULE'].update({
            'delete-stale-listening-sessions': {
                'task': 'superapp.apps.radio_crestin.tasks.delete_stale_listening_sessions.delete_stale_listening_sessions',
                'schedule': crontab(minute='*'),  # Every minute
            },
            'delete-old-anonymous-users': {
                'task': 'superapp.apps.radio_crestin.tasks.delete_old_anonymous_users.delete_old_anonymous_users',
                'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
            },
            'delete-old-now-playing-history': {
                'task': 'superapp.apps.radio_crestin.tasks.delete_old_now_playing_history.delete_old_now_playing_history',
                'schedule': crontab(hour=2, minute=15),  # Daily at 2:15 AM
            },
        })
