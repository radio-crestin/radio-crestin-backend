from django.urls import path, include
from . import views

# App-specific URL patterns
app_name = 'radio_crestin'

urlpatterns = [
    # Fast autocomplete API endpoints
    path('api/autocomplete/', views.api_autocomplete, name='api_autocomplete'),
    # Stations API v1 endpoint with caching
    path('api/v1/stations', views.api_v1_stations, name='api_v1_stations'),
]


def extend_superapp_urlpatterns(main_urlpatterns):
    """Extend main SuperApp URL patterns with radio_crestin app URLs."""
    main_urlpatterns.extend([
        path('radio-crestin/', include('superapp.apps.radio_crestin.urls')),
    ])