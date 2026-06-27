from django.urls import path, include
from . import views
from .views import PodHealthReportView, SessionRecordingView, DeviceRegistrationView

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
    ])
