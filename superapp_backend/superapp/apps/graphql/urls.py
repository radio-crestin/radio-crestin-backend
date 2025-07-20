from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView

from superapp.apps.graphql.schema import schema


def extend_superapp_urlpatterns(main_urlpatterns):
    main_urlpatterns += [
        path('graphql', csrf_exempt(GraphQLView.as_view(schema=schema)), name='graphql'),
    ]


def extend_superapp_admin_urlpatterns(main_admin_urlpatterns):
    pass
