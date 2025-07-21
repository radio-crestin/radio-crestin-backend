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
### Requirements
This module requires the `multi_tenant` app from https://github.com/django-superapp/django-superapp-multi-tenant

### Documentation
For a more detailed documentation, visit [https://django-superapp.bringes.io](https://django-superapp.bringes.io).
