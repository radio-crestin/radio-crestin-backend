from django.apps import AppConfig


class BackupsConfig(AppConfig):
    name = 'superapp.apps.backups'
    verbose_name = 'Backups and Restores'

    def ready(self):
        import superapp.apps.backups.signals
        
        # Manage PeriodicTask database records after Django is fully initialized
        from .schedule import manage_periodic_tasks
        manage_periodic_tasks()
