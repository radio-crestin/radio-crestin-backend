from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from superapp.apps.graphql.decorators import cors_exempt
from superapp.apps.graphql.graphql_get_view import GraphQLWithGetRedirectView


def extend_superapp_urlpatterns(main_urlpatterns):
    # Combined view: POST queries -> 302 GET, everything else -> Strawberry
    graphql_view = cors_exempt(csrf_exempt(GraphQLWithGetRedirectView.as_view()))

    main_urlpatterns += [
        path('graphql', graphql_view, name='graphql'),
        path('v1/graphql', graphql_view, name='graphql_v1'),
    ]

    # Auto-register REST API endpoints from all apps
    _register_rest_api_endpoints(main_urlpatterns)


def extend_superapp_admin_urlpatterns(main_admin_urlpatterns):
    pass


def _register_rest_api_endpoints(main_urlpatterns):
    """
    Auto-register REST API endpoints from all apps
    """
    try:
        # Import the registry which auto-discovers endpoints
        from superapp.apps.graphql.rest_api import RestApiRegistry
        import superapp.apps.graphql.rest_registry  # This triggers discovery
        from superapp.apps.graphql.rest_handler import create_rest_api_view

        # Get all registered endpoints
        endpoints = RestApiRegistry.get_all_endpoints()

        for path_pattern, endpoint_config in endpoints.items():
            # Create view for this endpoint
            view = create_rest_api_view(endpoint_config)

            # Add appropriate decorators
            if endpoint_config.cors_enabled:
                view = cors_exempt(csrf_exempt(view))
            else:
                view = csrf_exempt(view)

            # Register URL pattern
            main_urlpatterns.append(
                path(path_pattern, view, name=endpoint_config.name)
            )

    except ImportError as e:
        print(f"Could not import REST API registry: {e}")
        pass
