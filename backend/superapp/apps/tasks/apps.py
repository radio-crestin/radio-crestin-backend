from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superapp.apps.tasks'
    verbose_name = "Tasks"