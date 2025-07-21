from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from deepmerge import always_merger

def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] = [
        'superapp.apps.backups',
    ] + main_settings['INSTALLED_APPS']


    main_settings.update(
        always_merger.merge(
            {
                'BACKUPS': {
                    'BACKUP_TYPES': {
                        'all_models': {
                            'name': _('All Models'),
                            'description': _('Backup all models'),
                            'models': '*',
                            'exclude_models_from_import': [],
                        },
                        'essential_data': {
                            'name': _('Essential Data'),
                            'description': _('Backup essential data only'),
                            'models': [
                                'radio_crestin.stationsmetadatafetch',
                                'radio_crestin.stationtostationgroup',
                                'radio_crestin.stationstreams',
                                'radio_crestin.reviews',
                                'radio_crestin.posts',
                                'radio_crestin.stationsuptime',
                                'radio_crestin.stationsnowplaying',
                                'radio_crestin.stations',
                                'radio_crestin.stationgroups',
                                'radio_crestin.stationmetadatafetchcategories',
                            ],
                            'exclude_models_from_import': [],
                        },
                    },
                    'RETENTION': {
                        'MAX_BACKUPS': 10,
                    },
                }
            },
            main_settings,
        )
    )
    main_settings['UNFOLD']['SIDEBAR']['navigation'] += [
        {
            "title": _("Backups"),
            "icon": "database",
            "items": [
                {
                    "title": _("Backups"),
                    "icon": "backup",
                    "link": reverse_lazy("admin:backups_backup_changelist"),
                    "permission": lambda request: request.user.has_perm('backups.view_backup'),
                },
                {
                    "title": _("Restores"),
                    "icon": "restart_alt",
                    "link": reverse_lazy("admin:backups_restore_changelist"),
                    "permission": lambda request: request.user.has_perm('backups.view_restore'),
                },
            ]
        }
    ]
