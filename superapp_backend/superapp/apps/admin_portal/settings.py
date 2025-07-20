from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def extend_superapp_settings(main_settings):
    main_settings['STATICFILES_DIRS'] += [
        main_settings['BASE_DIR'] / "superapp" / "apps" / "admin_portal" / "static",
    ]
    main_settings['TEMPLATES'][0]['DIRS'] += [
        main_settings['BASE_DIR'] / "superapp" / "apps" / "admin_portal" / "templates",
    ]
    main_settings['INSTALLED_APPS'] = [
        'admin_confirm',
        'unfold',
        "unfold.contrib.filters",
        "unfold.contrib.forms",
        "unfold.contrib.inlines",
        "unfold.contrib.import_export",
        "unfold.contrib.guardian",
        "unfold.contrib.simple_history",
        "massadmin",
        'django_svelte_jsoneditor',
        'superapp.apps.admin_portal',
    ] + main_settings['INSTALLED_APPS'] + [
        "debug_toolbar",
        "import_export",
        "django_cleanup.apps.CleanupConfig",
    ]
    main_settings.update({
        'LOGIN_URL': "admin:login",
        'LOGIN_REDIRECT_URL': reverse_lazy("admin:index"),
    })

    main_settings['UNFOLD'] = {
        "SITE_HEADER": _("SuperApp"),
        "SITE_TITLE": _("SuperApp"),
        "SITE_SYMBOL": "settings",
        "SHOW_HISTORY": False,
        "SHOW_LANGUAGES": True,
        "SHOW_BACK_BUTTON": True,
        "TABS": [],
        "SITE_LOGO": {
            # "light": lambda request: static("images/logo-light.svg"),  # light mode
            # "dark": lambda request: static("images/logo-dark.svg"),  # dark mode
        },
        "COLORS": {
            "primary": {
                '50': '#eef2ff',
                '100': '#e0e7ff',
                '200': '#c7d2fe',
                '300': '#a5b4fc',
                '400': '#818cf8',
                '500': '#6366f1',
                '600': '#4f46e5',
                '700': '#4338ca',
                '800': '#3730a3',
                '900': '#312e81',
                '950': '#1e1b4b',
            },
        },
        "LOGIN": {
            # "image": lambda request: static("images/login-bg.jpg"),
        },
        "SIDEBAR": {
            "show_search": False,
            "show_all_applications": True,
            "navigation": [

            ]
        },
        "STYLES": [
            lambda request: static("admin_portal/css/styles.css"),
            lambda request: static("admin_portal/css/custom.css"),
        ],
        "SCRIPTS": [
            lambda request: static("admin_portal/js/apex.min.js"),
            lambda request: static("admin_portal/js/flowbite.min.js"),
            lambda request: static("admin_portal/js/jquery-3.7.1.min.js"),
            lambda request: static("admin_portal/js/modals.js"),
        ],
    }
    main_settings['MASSEDIT'] = {
        'ADD_ACTION_GLOBALLY': False,
    }
    main_settings['MIDDLEWARE'] += [
        'superapp.apps.admin_portal.middleware.RequestCacheMiddleware',
    ]
