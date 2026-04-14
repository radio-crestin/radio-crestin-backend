from django.apps import AppConfig


class BackupsConfig(AppConfig):
    name = 'superapp.apps.backups'
    verbose_name = 'Backups and Restores'

    def ready(self):
        import superapp.apps.backups.signals

        # Defer PeriodicTask management to after all apps are fully initialized
        # to avoid "Accessing the database during app initialization" warning.
        from django.db.models.signals import post_migrate
        post_migrate.connect(self._manage_periodic_tasks_after_migrate, sender=self)

    @staticmethod
    def _manage_periodic_tasks_after_migrate(sender, **kwargs):
        from .schedule import manage_periodic_tasks
        manage_periodic_tasks()
