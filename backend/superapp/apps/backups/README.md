# Django SuperApp - Sample App
### Getting Started
1. Setup the project using the instructions from https://django-superapp.bringes.io/
2. Setup `backups` app using the below instructions:
```bash
cd my_superapp;
cd superapp/apps;
django_superapp bootstrap-app \
    --template-repo https://github.com/django-superapp/django-superapp-backups ./backups;
cd ../../;
```
3. Configure the app in `settings.py`:
```python
from deepmerge import always_merger
from django.utils.translation import gettext_lazy as _


def extend_superapp_settings(main_settings):
    # Add tenant_models to the backup settings
    main_settings.update(
        always_merger.merge(
            {
                'BACKUPS': {
                    'BACKUP_TYPES': {
                        'common_models': {
                            'name': _('Common models'),
                            'description': _('Backup all common models'),
                            'models': [
                                "my_app.translation",
                                "my_app.translationvalues",
                                "my_app.location",
                                "auth.group",
                                "whatsapp.phonenumber",
                            ],
                            'exclude_models_from_import': [
                                "backups.backup",
                                "backups.restore",
                            ],
                        },
                        'organization': {
                            'name': _('Organization models'),
                            'description': _('Backup all organization models'),
                            'models': [
                                "my_app.organization",
                            ],
                            'exclude_models_from_import': [
                                "my_app.organizationdomainname",
                                "my_app.organizationuser",
                            ],
                        },
                    },
                }
            },
            main_settings,
        )
    )
```

### Requirements
This module requires the `multi_tenant` app from https://github.com/django-superapp/django-superapp-multi-tenant

### Documentation
For a more detailed documentation, visit [https://django-superapp.bringes.io](https://django-superapp.bringes.io).
