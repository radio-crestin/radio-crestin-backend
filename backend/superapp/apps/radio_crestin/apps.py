from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RadioCrestinConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superapp.apps.radio_crestin'
    verbose_name = _("Radio Crestin")

    def ready(self):
        import superapp.apps.radio_crestin.signals.station_config_version  # noqa: F401