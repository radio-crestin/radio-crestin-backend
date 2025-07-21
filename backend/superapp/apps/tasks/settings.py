import os

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] = \
        [
            'django_celery_beat',
            'django_celery_results',
        ] + main_settings['INSTALLED_APPS'] + [
            'superapp.apps.tasks',
        ]
    main_settings['UNFOLD']['TABS'] += [
        {
            "models": [
                "django_celery_beat.clockedschedule",
                "django_celery_beat.crontabschedule",
                "django_celery_beat.intervalschedule",
                "django_celery_beat.periodictask",
                "django_celery_beat.solarschedule",
            ],
            "items": [
                {
                    "title": _("Clocked"),
                    "icon": "hourglass_bottom",
                    "link": reverse_lazy(
                        "admin:django_celery_beat_clockedschedule_changelist"
                    ),
                },
                {
                    "title": _("Crontabs"),
                    "icon": "update",
                    "link": reverse_lazy(
                        "admin:django_celery_beat_crontabschedule_changelist"
                    ),
                },
                {
                    "title": _("Intervals"),
                    "icon": "arrow_range",
                    "link": reverse_lazy(
                        "admin:django_celery_beat_intervalschedule_changelist"
                    ),
                },
                {
                    "title": _("Periodic tasks"),
                    "icon": "task",
                    "link": reverse_lazy(
                        "admin:django_celery_beat_periodictask_changelist"
                    ),
                },
                {
                    "title": _("Solar events"),
                    "icon": "event",
                    "link": reverse_lazy(
                        "admin:django_celery_beat_solarschedule_changelist"
                    ),
                },
            ],
        },
    ]
    main_settings['UNFOLD']['SIDEBAR']['navigation'] += [
        {
            "title": _("Celery Management"),
            "icon": "add_task",
            "separator": True,
            "items": [
                {
                    "title": _("Tasks Results"),
                    "icon": "add_task",
                    "link": reverse_lazy("admin:django_celery_results_taskresult_changelist"),
                    "permission": lambda request: request.user.has_perm('django_celery_results.view_taskresult'),
                },
                {
                    "title": _("Group Results"),
                    "icon": "atr",
                    "link": reverse_lazy("admin:django_celery_results_groupresult_changelist"),
                    "permission": lambda request: request.user.has_perm('django_celery_results.view_groupresult'),
                },
                {
                    "title": _("Scheduled Tasks"),
                    "icon": "task_alt",
                    "link": reverse_lazy(
                        "admin:django_celery_beat_clockedschedule_changelist",
                    ),
                    "permission": lambda request: request.user.has_perm('django_celery_beat.view_clockedschedule'),
                },
            ],
        },
    ]
    ######################################################################
    # Celery
    # Docs: https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
    ######################################################################
    main_settings.update({
        'CELERY_BROKER_URL': os.environ.get('REDIS_BROKER_URL'),
        'CELERY_ACCEPT_CONTENT': ['application/json'],
        'CELERY_TASK_SERIALIZER': 'json',
        'CELERY_RESULT_SERIALIZER': 'json',
        'CELERY_TASK_TRACK_STARTED': True,
        'CELERY_RESULT_BACKEND': 'django-db',
        'CELERY_CACHE_BACKEND': 'django-cache',
        'CELERY_RESULT_EXTENDED': True,
        'CELERY_TASK_TIME_LIMIT': 60 * 60,  # 1h
    })

    ######################################################################
    # Celery Beat
    # Docs: https://django-celery-beat.readthedocs.io/en/latest/
    ######################################################################
    main_settings.update({
        'CELERY_BEAT_SCHEDULER': 'django_celery_beat.schedulers:DatabaseScheduler',
        'DJANGO_CELERY_BEAT_TZ_AWARE': False,
    })

    main_settings['CACHES'] = {
        'default': {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ.get('REDIS_BROKER_URL'),
        }
    }
