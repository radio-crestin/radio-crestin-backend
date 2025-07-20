from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy


def extend_superapp_settings(main_settings):
    """Extend main SuperApp settings with radio_crestin app configuration."""
    
    # Add this app to INSTALLED_APPS
    main_settings['INSTALLED_APPS'] += ['superapp.apps.radio_crestin']
    
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
            ]
        },
    ]