from django.apps import AppConfig


class GraphQLConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superapp.apps.graphql'
    verbose_name = 'GraphQL API'
