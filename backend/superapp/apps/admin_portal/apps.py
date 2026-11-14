from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'superapp.apps.admin_portal'
    default = True

    def ready(self):
        from . import unfold_patches
        unfold_patches.apply()
