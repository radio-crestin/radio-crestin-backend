from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.views import View
from django.shortcuts import redirect
import json
import logging

from .models import Songs, Artists
from .services import AutocompleteService
from .services.share_link_service import ShareLinkService

logger = logging.getLogger(__name__)


class FastSongAutocompleteView(AutocompleteJsonView):
    """Fast autocomplete view for songs using trigram indexes"""

    def get_queryset(self):
        """Use the optimized service for fast search"""
        if not self.term or len(self.term.strip()) < 2:
            return Songs.objects.none()

        # Use the autocomplete service for fast trigram-based search
        return AutocompleteService.search_songs(self.term.strip(), limit=20)

    def get_paginator(self, *args, **kwargs):
        """Override paginator since we handle limiting in the service"""
        from django.core.paginator import Paginator
        return Paginator(list(self.get_queryset()), 20)


class FastArtistAutocompleteView(AutocompleteJsonView):
    """Fast autocomplete view for artists using trigram indexes"""

    def get_queryset(self):
        """Use the optimized service for fast search"""
        if not self.term or len(self.term.strip()) < 2:
            return Artists.objects.none()

        # Use the autocomplete service for fast trigram-based search
        return AutocompleteService.search_artists(self.term.strip(), limit=20)

    def get_paginator(self, *args, **kwargs):
        """Override paginator since we handle limiting in the service"""
        from django.core.paginator import Paginator
        return Paginator(list(self.get_queryset()), 20)


class FastAutocompleteJsonView(AutocompleteJsonView):
    """
    Generic fast autocomplete view that can be configured for any model.
    Uses the service layer for optimized trigram-based searching.
    """
    service_method = None

    def get_queryset(self):
        """Use the configured service method for fast search"""
        if not self.term or len(self.term.strip()) < 2:
            return self.model_admin.model.objects.none()

        if not self.service_method:
            # Fallback to default Django behavior
            qs = self.model_admin.get_queryset(self.request)
            qs = qs.complex_filter(self.source_field.get_limit_choices_to())
            qs, search_use_distinct = self.model_admin.get_search_results(
                self.request, qs, self.term
            )
            if search_use_distinct:
                qs = qs.distinct()
            return qs

        # Use the configured service method
        return self.service_method(self.term.strip(), limit=20)

    def get_paginator(self, *args, **kwargs):
        """Override paginator since we handle limiting in the service"""
        from django.core.paginator import Paginator
        return Paginator(list(self.get_queryset()), 20)


def api_autocomplete(request):
    """
    Simple API endpoint for autocomplete that returns JSON data
    Useful for frontend applications that need autocomplete data
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'combined')
    limit = int(request.GET.get('limit', 10))

    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    try:
        suggestions = AutocompleteService.get_autocomplete_suggestions(
            query=query,
            search_type=search_type,
            limit=limit
        )
        return JsonResponse({'results': suggestions})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




class ShareLinkRedirectView(View):
    """Handle share link redirects and track visits"""
    
    def get_device_type(self, user_agent):
        """Detect device type from user agent string"""
        if 'Windows' in user_agent or 'Macintosh' in user_agent:
            return 'desktop'
        elif 'iPhone' in user_agent or 'iPad' in user_agent:
            return 'ios'
        elif 'Android' in user_agent:
            return 'android'
        elif 'Huawei' in user_agent:
            return 'huawei'
        else:
            return 'unknown'
    
    def get_android_install_page(self, desktop_url, google_play_url):
        """Generate Android app installation HTML page"""
        html_template = """
<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Radio Crestin</title>
  <style>
    body {
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100vh;
      margin: 0;
      font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol";
      background-color: #f4f4f4;
      padding-top: 10vh;
    }
    img {
      max-width: 80%;
      height: auto;
      border-radius: 10px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
    }
    h1 {
      font-weight: 600;
      font-size: 2.5rem;
      margin-top: 13px;
    }
    p {
      text-align: center;
      margin-top: 20px;
      font-size: 1.2rem;
      color: black;
      font-weight: 300;
    }
    .buttons {
      display: flex;
      gap: 10px;
      margin-top: 20px;
    }
    #no-thanks {
      text-decoration: none;
      color: black;
      font-size: 1.2rem;
      position: absolute;
      bottom: 35px;
    }
    .google-play-button:hover {
      box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
    }
    .google-play-button:active {
      box-shadow: 0 1px 2px rgba(0,0,0,0.2) !important;
    }
  </style>
</head>
<body>
<div id="logo">
  <svg width="64" height="64" viewBox="0 0 754 745" fill="none" xmlns="http://www.w3.org/2000/svg">
    <g clip-path="url(#clip0_609_165)">
      <rect y="-9" width="754" height="754" rx="132" fill="#FF0057"/>
      <rect y="-9" width="754" height="754" rx="132" fill="#FF0057"/>
      <g clip-path="url(#clip1_609_165)">
        <path d="M649.62 254.996C646.943 253.862 643.906 253.265 640.814 253.265C637.723 253.265 634.686 253.862 632.009 254.996C572.659 280.829 527.927 330.042 510.492 351.225L497.636 367.5L480.025 388.425C449.029 420.587 390.208 470.575 325.223 470.575C243.332 470.575 171.126 391.137 151.93 368.017C171.126 344.896 243.155 265.458 325.223 265.458C387.567 265.458 444.45 311.7 476.327 343.862L481.258 337.662C481.258 337.662 487.598 331.075 497.636 321.517C460.124 285.35 397.781 239.108 324.167 239.108C208.109 239.108 118.645 356.262 114.947 361.3L110.896 367.5L115.651 373.7C119.349 378.737 208.814 495.892 324.871 495.892C413.983 495.892 487.245 426.917 518.593 392.558C517.889 393.333 538.67 367.5 538.67 367.5L539.903 366.079C549.423 353.516 560.507 341.625 573.012 330.558C587.955 316.416 604.832 303.431 623.379 291.808V443.45C599.241 428.309 577.872 410.943 559.803 391.783L556.985 395.142L539.374 415.679C564.049 441.133 595.206 462.845 631.128 479.617C633.795 480.778 636.833 481.401 639.934 481.425C643.006 481.371 646.02 480.797 648.739 479.746C651.427 478.608 653.657 476.969 655.203 474.996C656.749 473.022 657.557 470.784 657.545 468.508V266.233C657.649 264.019 656.975 261.822 655.587 259.854C654.199 257.886 652.144 256.213 649.62 254.996Z" fill="white"/>
      </g>
    </g>
    <defs>
      <clipPath id="clip0_609_165">
        <rect width="754" height="745" fill="white"/>
      </clipPath>
      <clipPath id="clip1_609_165">
        <rect width="634" height="465" fill="white" transform="translate(60 135)"/>
      </clipPath>
    </defs>
  </svg>
</div>
<h1>Radio Crestin</h1>

<p>Instaleaza aplicatia mobila.</p>
<div class="buttons">
  <script>
    setTimeout(() => {
      window.location = "{{ google_play_url }}"
    }, 500);
  </script>
  <a href="{{ google_play_url }}" class="google-play-button" style="display: inline-flex; align-items: center; height: 60px; min-width: 200px; padding: 0 20px 0 16px; background-color: #000000; border-radius: 8px; text-decoration: none; color: white; font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.25); transition: box-shadow 0.15s;">
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 48 48" style="margin-right: 16px; flex-shrink: 0;">
      <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
      <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
      <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
      <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
    </svg>
    <div style="display: flex; flex-direction: column; justify-content: center; line-height: 1.25;">
      <span style="font-size: 11px; font-weight: 400; letter-spacing: 0.25px; margin-bottom: 1px;">DESCARCĂ DIN</span>
      <span style="font-size: 16px; font-weight: 500; letter-spacing: 0;">Google Play</span>
    </div>
  </a>
</div>
<a href="{{ desktop_url }}" id="no-thanks">Continuă în browser</a>
</body>
</html>
"""
        return html_template.replace('{{ desktop_url }}', desktop_url).replace('{{ google_play_url }}', google_play_url)
    
    def get(self, request, *args, **kwargs):
        """Process share link and redirect to appropriate destination"""
        logger = logging.getLogger(__name__)
        
        # Get station from URL path
        station_slug = kwargs.get('station_path', '')
        
        # Build base redirect URL with station path
        base_url = 'https://www.radiocrestin.ro'
        if station_slug:
            default_redirect = f"{base_url}/{station_slug}"
        else:
            default_redirect = base_url
        
        # Get share_id from query parameter
        share_id = request.GET.get('s')
        if not share_id:
            # No share link, redirect to main site with path preserved
            return redirect(default_redirect)
        
        # Get share link from service
        share_link = ShareLinkService.get_share_link_by_id(share_id)
        if not share_link:
            # Invalid share link, redirect to main site with path preserved
            logger.warning(f"Invalid share link attempted: {share_id}")
            return redirect(default_redirect)
        
        # Get visitor information
        visitor_ip = request.META.get('REMOTE_ADDR')
        visitor_user_agent = request.META.get('HTTP_USER_AGENT', '')
        visitor_referer = request.META.get('HTTP_REFERER', '')
        
        # Get or create session ID for tracking unique visitors
        visitor_session_id = ''
        if hasattr(request, 'session'):
            if not request.session.session_key:
                request.session.create()
            visitor_session_id = request.session.session_key
        
        # Check if visitor is the share link creator (don't count their visits)
        is_creator = False
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'anonymous_id'):
                is_creator = request.user.anonymous_id == share_link.user.anonymous_id
        
        # Track visit if not the creator
        if not is_creator:
            ShareLinkService.track_visit(
                share_id=share_id,
                visitor_ip=visitor_ip,
                visitor_user_agent=visitor_user_agent,
                visitor_referer=visitor_referer,
                visitor_session_id=visitor_session_id
            )
        
        # Detect device type
        device_type = self.get_device_type(visitor_user_agent)
        
        # Get ref parameter for tracking
        ref = request.GET.get('ref', 'share')
        
        # Build target URL
        base_url = 'https://www.radiocrestin.ro'
        if station_slug:
            target_url = f"{base_url}/{station_slug}?ref={ref}"
        else:
            target_url = f"{base_url}?ref={ref}"
        
        # Handle different device types
        if device_type in ['desktop', 'unknown']:
            return redirect(target_url)
        
        elif device_type == 'ios':
            # Redirect to App Store
            app_store_url = "https://apps.apple.com/app/6451270471"
            return redirect(app_store_url)
        
        elif device_type == 'android':
            # Show Android installation page
            google_play_url = f"market://details?id=com.radiocrestin.radio_crestin&url=radiocrestin%3A%2F%2F{station_slug}&referrer={ref}"
            html_content = self.get_android_install_page(target_url, google_play_url)
            return HttpResponse(html_content, content_type='text/html')
        
        elif device_type == 'huawei':
            # Redirect to Huawei AppGallery
            huawei_url = "https://appgallery.huawei.com/app/C109055331"
            return redirect(huawei_url)
        
        # Default fallback
        return redirect(target_url)


def api_landing_view(request):
    """API landing page with links to REST docs and GraphQL playground."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radio Crestin API</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .container { max-width: 600px; width: 100%; padding: 2rem; }
  h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; color: #1a1a2e; }
  p { color: #6b7280; margin-bottom: 2rem; font-size: 0.95rem; }
  .cards { display: flex; flex-direction: column; gap: 1rem; }
  a.card { display: block; padding: 1.25rem 1.5rem; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; text-decoration: none; transition: box-shadow 0.15s, border-color 0.15s; }
  a.card:hover { border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.12); }
  .card-title { font-size: 1.1rem; font-weight: 600; color: #1a1a2e; margin-bottom: 0.25rem; }
  .card-desc { font-size: 0.85rem; color: #6b7280; }
  .badge { display: inline-block; font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px; margin-left: 0.5rem; vertical-align: middle; }
  .badge-blue { background: #dbeafe; color: #1d4ed8; }
  .badge-purple { background: #ede9fe; color: #6d28d9; }
</style>
</head>
<body>
<div class="container">
  <h1>Radio Crestin API</h1>
  <p>Choose an API interface to get started.</p>
  <div class="cards">
    <a href="/api/v1/docs/" class="card">
      <div class="card-title">REST API <span class="badge badge-blue">Recommended</span></div>
      <div class="card-desc">CDN-cached, fast, with interactive Scalar documentation.</div>
    </a>
    <a href="/graphql" class="card">
      <div class="card-title">GraphQL API <span class="badge badge-purple">Flexible</span></div>
      <div class="card-desc">Flexible queries with the GraphiQL playground.</div>
    </a>
  </div>
</div>
</body>
</html>'''
    return HttpResponse(html, content_type='text/html')


def api_schema_view(request):
    """OpenAPI 3.0 schema for REST API endpoints with sample responses."""
    import time
    now_ts = int(time.time())
    one_hour_ago_ts = now_ts - 3600

    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "Radio Crestin API",
            "version": "1.0.0",
            "description": "Christian Radio Stations Directory API. All endpoints return data wrapped in a `data` key (GraphQL convention).",
        },
        "servers": [
            {"url": "/", "description": "Current server"},
        ],
        "paths": {
            "/api/v1/stations": {
                "get": {
                    "summary": "Get all stations",
                    "description": "Returns all active radio stations with full details including streams, uptime, now playing, posts, and reviews. If `timestamp` is omitted, redirects (302) to a timestamped URL rounded to 10s for CDN caching.",
                    "operationId": "getStations",
                    "parameters": [
                        {"name": "timestamp", "in": "query", "description": "Unix timestamp for cache control. Omit to auto-redirect with current timestamp.", "schema": {"type": "integer"}},
                        {"name": "station_slugs", "in": "query", "description": "Comma-separated list of station slugs to include. Only these stations will be returned.", "schema": {"type": "string"}, "example": "aripi-spre-cer,radio-vocea-evangheliei"},
                        {"name": "exclude_station_slugs", "in": "query", "description": "Comma-separated list of station slugs to exclude. These stations will be omitted from results.", "schema": {"type": "string"}, "example": "radio-trinitas"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Stations data",
                            "content": {"application/json": {"example": {
                                "data": {
                                    "stations": [
                                        {
                                            "id": 0, "slug": "aripi-spre-cer", "order": 0,
                                            "title": "Aripi Spre Cer", "website": "https://aripisprecer.ro",
                                            "email": "", "stream_url": "https://stream.aripisprecer.ro/listen",
                                            "proxy_stream_url": "https://proxy.radio-crestin.com/https://stream.aripisprecer.ro/listen",
                                            "hls_stream_url": "https://hls-staging.radio-crestin.com/aripi-spre-cer/index.m3u8",
                                            "thumbnail_url": "https://cdn.radio-crestin.com/stations/aripi-spre-cer.webp",
                                            "total_listeners": 95, "radio_crestin_listeners": 5,
                                            "description": None, "description_action_title": None, "description_link": None,
                                            "feature_latest_post": True, "facebook_page_id": None,
                                            "station_streams": [{"order": 0, "type": "audio/mpeg", "stream_url": "https://stream.aripisprecer.ro/listen"}],
                                            "posts": [{"id": 10, "title": "Emisiune noua", "description": "...", "link": "https://...", "published": "2026-02-20T12:00:00+00:00"}],
                                            "uptime": {"is_up": True, "latency_ms": 181, "timestamp": "2026-02-23T12:00:00+00:00"},
                                            "now_playing": {"id": 1, "timestamp": "2026-02-23T12:00:00+00:00", "song": {"id": 2558, "name": "Chiar daca muntii", "thumbnail_url": "https://pictures.aripisprecer.ro/general/az_42540_VA%2052_Diana%20Scridon%20%26%20Ovidiu%20Opris.jpg", "artist": {"id": 1382, "name": "Diana Scridon & Ovidiu Opris", "thumbnail_url": None}}},
                                            "reviews": [], "reviews_stats": {"number_of_reviews": 12, "average_rating": 4.8},
                                        }
                                    ],
                                    "station_groups": [
                                        {"id": 1, "name": "Populare", "order": 0, "slug": "populare", "station_to_station_groups": [{"station_id": 0, "order": 0}]}
                                    ],
                                }
                            }}},
                        },
                        "302": {"description": "Redirect to timestamped URL when `timestamp` is omitted"},
                        "400": {"description": "Timestamp is in the future or invalid format"},
                    },
                },
            },
            "/api/v1/stations-metadata": {
                "get": {
                    "summary": "Get station metadata (lightweight)",
                    "description": "Returns lightweight station metadata (uptime + now_playing only). Much smaller payload than `/api/v1/stations`. Use `changes_from_timestamp` for efficient polling (only returns stations that changed).",
                    "operationId": "getStationsMetadata",
                    "parameters": [
                        {"name": "timestamp", "in": "query", "description": "Unix timestamp for cache control and historical lookup. Omit to auto-redirect with current timestamp.", "schema": {"type": "integer"}},
                        {"name": "changes_from_timestamp", "in": "query", "description": "Only return stations whose metadata changed after this timestamp. For polling every 30s, set to `timestamp - 30`.", "schema": {"type": "integer"}},
                        {"name": "station_slugs", "in": "query", "description": "Comma-separated list of station slugs to include. Only these stations will be returned.", "schema": {"type": "string"}, "example": "aripi-spre-cer,radio-vocea-evangheliei"},
                        {"name": "exclude_station_slugs", "in": "query", "description": "Comma-separated list of station slugs to exclude. These stations will be omitted from results.", "schema": {"type": "string"}, "example": "radio-trinitas"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Station metadata list",
                            "content": {"application/json": {"example": {
                                "data": {
                                    "stations_metadata": [
                                        {
                                            "id": 0, "slug": "aripi-spre-cer", "title": "Aripi Spre Cer",
                                            "uptime": {"is_up": True, "latency_ms": 181, "timestamp": "2026-02-23T12:00:00+00:00"},
                                            "now_playing": {
                                                "timestamp": "2026-02-23T12:00:00+00:00", "listeners": 95,
                                                "song": {"id": 2558, "name": "Chiar daca muntii", "thumbnail_url": "https://pictures.aripisprecer.ro/general/az_42540_VA%2052_Diana%20Scridon%20%26%20Ovidiu%20Opris.jpg", "artist": {"id": 1382, "name": "Diana Scridon & Ovidiu Opris", "thumbnail_url": None}},
                                            },
                                        }
                                    ]
                                }
                            }}},
                        },
                        "302": {"description": "Redirect to timestamped URL when `timestamp` is omitted"},
                        "400": {"description": "Timestamp is in the future or invalid format"},
                    },
                },
            },
            "/api/v1/stations-metadata-history": {
                "get": {
                    "summary": "Get station metadata history",
                    "description": "Returns historical metadata snapshots for a specific station within a time range. Maximum range is 24 hours. Defaults: `from_timestamp` = now - 1 hour, `to_timestamp` = now.",
                    "operationId": "getStationsMetadataHistory",
                    "parameters": [
                        {"name": "station_slug", "in": "query", "required": True, "description": "Station slug identifier", "schema": {"type": "string"}, "example": "aripi-spre-cer"},
                        {"name": "from_timestamp", "in": "query", "description": "Start of time range (Unix timestamp). Defaults to now - 1 hour.", "schema": {"type": "integer"}, "example": one_hour_ago_ts},
                        {"name": "to_timestamp", "in": "query", "description": "End of time range (Unix timestamp). Defaults to now.", "schema": {"type": "integer"}, "example": now_ts},
                    ],
                    "responses": {
                        "200": {
                            "description": "Station metadata history",
                            "content": {"application/json": {"example": {
                                "data": {
                                    "stations_metadata_history": {
                                        "station_id": 0, "station_slug": "aripi-spre-cer", "station_title": "Aripi Spre Cer",
                                        "from_timestamp": one_hour_ago_ts, "to_timestamp": now_ts, "count": 3,
                                        "history": [
                                            {"timestamp": "2026-02-23T11:00:00+00:00", "listeners": 102, "song": {"id": 2401, "name": "Battle Belongs", "thumbnail_url": "https://pictures.aripisprecer.ro/general/az_42550_VA%2052_Phil%20Wickham.jpg", "artist": {"id": 23, "name": "Phil Wickham", "thumbnail_url": None}}},
                                            {"timestamp": "2026-02-23T11:30:00+00:00", "listeners": 100, "song": {"id": 2558, "name": "Chiar daca muntii", "thumbnail_url": "https://pictures.aripisprecer.ro/general/az_42540_VA%2052_Diana%20Scridon%20%26%20Ovidiu%20Opris.jpg", "artist": {"id": 1382, "name": "Diana Scridon & Ovidiu Opris", "thumbnail_url": None}}},
                                            {"timestamp": "2026-02-23T12:00:00+00:00", "listeners": 95, "song": {"id": 2558, "name": "Chiar daca muntii", "thumbnail_url": "https://pictures.aripisprecer.ro/general/az_42540_VA%2052_Diana%20Scridon%20%26%20Ovidiu%20Opris.jpg", "artist": {"id": 1382, "name": "Diana Scridon & Ovidiu Opris", "thumbnail_url": None}}},
                                        ],
                                    }
                                }
                            }}},
                        },
                    },
                },
            },
            "/api/v1/reviews": {
                "get": {
                    "summary": "Get reviews",
                    "description": "Returns verified reviews. Filter by `station_id` or `station_slug`. If `timestamp` is omitted, redirects to a timestamped URL for CDN caching.",
                    "operationId": "getReviews",
                    "parameters": [
                        {"name": "station_id", "in": "query", "description": "Filter by station ID", "schema": {"type": "integer"}, "example": 0},
                        {"name": "station_slug", "in": "query", "description": "Filter by station slug (alternative to station_id)", "schema": {"type": "string"}, "example": "aripi-spre-cer"},
                        {"name": "timestamp", "in": "query", "description": "Unix timestamp for cache control", "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Reviews list",
                            "content": {"application/json": {"example": {
                                "data": {
                                    "reviews": [
                                        {"id": 1, "station_id": 0, "stars": 5, "message": "Foarte frumos!", "created_at": "2026-02-20T10:00:00+00:00", "updated_at": "2026-02-20T10:00:00+00:00"},
                                        {"id": 2, "station_id": 0, "stars": 4, "message": "Bun", "created_at": "2026-02-19T08:00:00+00:00", "updated_at": "2026-02-19T08:00:00+00:00"},
                                    ]
                                }
                            }}},
                        },
                        "302": {"description": "Redirect to timestamped URL when `timestamp` is omitted"},
                    },
                },
            },
            "/api/v1/reviews/": {
                "post": {
                    "summary": "Submit a review",
                    "description": "Submit or update a station review. Reviews are unique per IP address and station. Provide either `station_id` or `station_slug`.",
                    "operationId": "submitReview",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["stars"],
                                    "properties": {
                                        "station_id": {"type": "integer", "description": "Station ID (provide this or station_slug)"},
                                        "station_slug": {"type": "string", "description": "Station slug (provide this or station_id)"},
                                        "stars": {"type": "integer", "minimum": 0, "maximum": 5},
                                        "message": {"type": "string", "nullable": True},
                                        "user_identifier": {"type": "string", "nullable": True},
                                    },
                                },
                                "examples": {
                                    "with_station_id": {
                                        "summary": "Using station_id",
                                        "value": {"station_id": 0, "stars": 5, "message": "Foarte frumos!"},
                                    },
                                    "with_station_slug": {
                                        "summary": "Using station_slug",
                                        "value": {"station_slug": "aripi-spre-cer", "stars": 5, "message": "Foarte frumos!"},
                                    },
                                },
                            },
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Review submitted",
                            "content": {"application/json": {"example": {
                                "data": {
                                    "submit_review": {
                                        "success": True, "message": "Review created successfully", "created": True,
                                        "review": {"id": 42, "station_id": 0, "stars": 5, "message": "Foarte frumos!", "user_identifier": None, "created_at": "2026-02-23T12:00:00+00:00", "updated_at": "2026-02-23T12:00:00+00:00", "verified": False},
                                    }
                                }
                            }}},
                        },
                    },
                },
            },
        },
    }
    return JsonResponse(schema)


def api_docs_view(request):
    """Scalar API documentation UI with client-side dynamic timestamp defaults."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radio Crestin API Docs</title>
</head>
<body>
<script id="api-reference" data-configuration='{"spec":{"url":"/api/v1/schema/"}}'></script>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
</body>
</html>'''
    return HttpResponse(html, content_type='text/html')
