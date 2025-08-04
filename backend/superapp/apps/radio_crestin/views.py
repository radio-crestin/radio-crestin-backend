from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.shortcuts import redirect
import json
from strawberry.django.context import StrawberryDjangoContext
import logging

from .models import Songs, Artists
from .services import AutocompleteService
from .services.share_link_service import ShareLinkService
from .constants import STATIONS_GRAPHQL_QUERY
from superapp.apps.graphql.schema import schema


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


def api_v1_stations(request):
    """
    API endpoint that redirects to a timestamped URL and executes GraphQL query with cache headers.
    """
    # Get current timestamp rounded to 10 seconds
    current_timestamp = timezone.now().timestamp()
    rounded_timestamp = int(current_timestamp // 10) * 10

    # Check if we already have the timestamp parameter
    timestamp_param = request.GET.get('timestamp')

    if not timestamp_param:
        # Redirect to the same URL with timestamp parameter
        redirect_url = f"{request.path}?timestamp={rounded_timestamp}"
        return HttpResponseRedirect(redirect_url)

    # Execute GraphQL query
    graphql_query = STATIONS_GRAPHQL_QUERY

    try:
        # Create a response object that will be used for the context
        response = HttpResponse()

        # Create a context for the GraphQL execution
        context = StrawberryDjangoContext(request=request, response=response)

        # Execute the GraphQL query directly using Strawberry schema
        result = schema.execute_sync(
            graphql_query,
            context_value=context
        )

        # Prepare response data
        response_data = {"data": result.data}

        if result.errors:
            response_data["errors"] = [
                {"message": str(error)} for error in result.errors
            ]

        # Create response with cache headers
        json_response = JsonResponse(response_data)
        json_response['Cache-Control'] = 'public, max-age=14400, immutable'

        return json_response

    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


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
  <a href="{{ google_play_url }}" class="store-button">
    <svg width="193px" viewBox="0 0 135 40" version="1.1" xmlns="http://www.w3.org/2000/svg">
      <g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
        <rect fill="#000000" x="0" y="0" width="135" height="40" rx="5"></rect>
        <path d="M130,0.8 C132.319596,0.8 134.2,2.68040405 134.2,5 L134.2,35 C134.2,37.3195959 132.319596,39.2 130,39.2 L5,39.2 C2.68040405,39.2 0.8,37.3195959 0.8,35 L0.8,5 C0.8,2.68040405 2.68040405,0.8 5,0.8 L130,0.8 L130,0.8 Z M130,0 L5,0 C2.23857625,0 0,2.23857625 0,5 L0,35 C0,37.7614237 2.23857625,40 5,40 L130,40 C132.761424,40 135,37.7614237 135,35 L135,5 C135,2.23857625 132.761424,0 130,0 Z" fill="#A6A6A6"></path>
        <path d="M47.42,10.24 C47.4543536,10.981231 47.1832676,11.7041269 46.67,12.24 C46.0964498,12.8358032 45.2964838,13.1594258 44.47,13.13 C43.2023403,13.1200788 42.0641482,12.3512162 41.5816918,11.1789127 C41.0992355,10.0066092 41.3665355,8.65932246 42.26,7.76 C42.840533,7.16732597 43.6405789,6.84151543 44.47,6.86 C44.8927576,6.85859143 45.3113359,6.94366832 45.7,7.11 C46.0618545,7.25595356 46.3839841,7.48555656 46.64,7.78 L46.11,8.31 C45.7053468,7.82867645 45.0978848,7.56568987 44.47,7.6 C43.8388494,7.59690387 43.2336793,7.85108766 42.794036,8.30393914 C42.3543927,8.75679062 42.1182283,9.36921739 42.14,10 C42.1266019,10.9531897 42.6879765,11.8208395 43.5629333,12.1992583 C44.43789,12.5776771 45.4545926,12.3925456 46.14,11.73 C46.4477095,11.3965366 46.625183,10.9635013 46.64,10.51 L44.47,10.51 L44.47,9.79 L47.38,9.79 C47.4066731,9.93851412 47.4200594,10.0891096 47.42,10.24 L47.42,10.24 Z" stroke="#FFFFFF" stroke-width="0.2" fill="#FFFFFF"></path>
        <text font-family="Roboto-Regular, Roboto" font-size="10" font-weight="normal" fill="#FFFFFF">
          <tspan x="50" y="17">GET IT ON</tspan>
        </text>
        <text font-family="Roboto-Medium, Roboto" font-size="14" font-weight="400" fill="#FFFFFF">
          <tspan x="50" y="30">Google Play</tspan>
        </text>
      </g>
    </svg>
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


def get_share_link_api(request, anonymous_id):
    """API endpoint to get or create share link for a user"""
    try:
        # Get share link info from service (will create user and link if needed)
        result = ShareLinkService.get_share_link_info(anonymous_id)
        
        # Add CORS headers if needed
        response = JsonResponse(result)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET'
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_share_link_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)
