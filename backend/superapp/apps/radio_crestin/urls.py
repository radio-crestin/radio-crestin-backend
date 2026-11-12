from django.urls import path, include
from . import views
from .views import (
    PodHealthReportView, SessionRecordingView, DeviceRegistrationView, StationPlaylistUpdateView,
    AnnouncementListView, AnnouncementDetailView, AnnouncementEventsView,
    FormPageView, FormResultsView, FormSubmitView,
)

# App-specific URL patterns
app_name = 'radio_crestin'

urlpatterns = [
    # Fast autocomplete API endpoints
    path('api/autocomplete/', views.api_autocomplete, name='api_autocomplete'),
]


def extend_superapp_urlpatterns(main_urlpatterns):
    """Extend main SuperApp URL patterns with radio_crestin app URLs."""
    from .views import api_landing_view, api_schema_view, api_docs_view

    main_urlpatterns.extend([
        path('radio-crestin/', include('superapp.apps.radio_crestin.urls')),
        path('api/', api_landing_view, name='api_landing'),
        path('api/v1/schema/', api_schema_view, name='api_schema'),
        path('api/v1/docs/', api_docs_view, name='api_docs'),
        # Pod health reporting API (for streaming pods)
        path('api/v1/pod-health/', PodHealthReportView.as_view(), name='api_v1_pod_health'),
        # Per-device session replay (screen recording) decision for the app
        path('api/v1/session-recording/<str:device_id>/', SessionRecordingView.as_view(), name='api_v1_session_recording'),
        # Device/client registration upsert (called by the app on every launch)
        path('api/v1/devices/register/', DeviceRegistrationView.as_view(), name='api_v1_device_register'),
        # External playlist update (per-station X-Api-Key, full replace)
        path('api/v1/station-playlist/update', StationPlaylistUpdateView.as_view(), name='api_v1_station_playlist_update'),
        # Announcements card (website + apps): list targeted per device, one by slug, client events
        path('api/v1/announcements/', AnnouncementListView.as_view(), name='api_v1_announcements'),
        path('api/v1/announcements/events/', AnnouncementEventsView.as_view(), name='api_v1_announcement_events'),
        path('api/v1/announcements/<slug:slug>/', AnnouncementDetailView.as_view(), name='api_v1_announcement_detail'),
        # Forms opened from announcements (under /api/: the public ingress routes only /api, /graphql, /health)
        path('api/v1/forms/<slug:slug>/page/', FormPageView.as_view(), name='api_v1_form_page'),
        path('api/v1/forms/<slug:slug>/submit/', FormSubmitView.as_view(), name='api_v1_form_submit'),
        path('api/v1/forms/<slug:slug>/results/', FormResultsView.as_view(), name='api_v1_form_results'),
    ])
