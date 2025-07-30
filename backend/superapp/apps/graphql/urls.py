from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView

from superapp.apps.graphql.decorators import cors_exempt
from superapp.apps.graphql.schema import schema
from superapp.apps.graphql.views import GraphQLProxyView


def extend_superapp_urlpatterns(main_urlpatterns):
    main_urlpatterns += [
        path('graphql', cors_exempt(csrf_exempt(GraphQLView.as_view(schema=schema))), name='graphql'),
        path('v1/graphql', cors_exempt(csrf_exempt(GraphQLProxyView.as_view(schema=schema))), name='graphql_v1_proxy'),
        path('v2/graphql', cors_exempt(csrf_exempt(GraphQLView.as_view(schema=schema))), name='graphql_v2'),
    ]


def extend_superapp_admin_urlpatterns(main_admin_urlpatterns):
    pass
