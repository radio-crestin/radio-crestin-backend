import strawberry_django

from superapp.apps.authentication.models import User


@strawberry_django.type(User, fields="__all__")
class SampleType:
    pass
