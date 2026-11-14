"""
Storage app settings configuration.
Extends superapp settings with storage configuration.
"""
from .config import StorageConfig


def extend_superapp_settings(main_settings):
    """
    Extend superapp settings with storage configuration.

    Args:
        main_settings: Main Django settings dictionary
    """
    # Add storage app to installed apps, before django.contrib.staticfiles:
    # its collectstatic command replaces Django's (the first app wins).
    installed = main_settings['INSTALLED_APPS']
    installed.insert(installed.index('django.contrib.staticfiles'), 'superapp.apps.storage')

    # Override STORAGES with our storage configuration
    main_settings['STORAGES'] = StorageConfig.get_storage_settings()
    
    # Override STATIC_URL with our dynamic configuration
    main_settings['STATIC_URL'] = StorageConfig.get_static_url()
