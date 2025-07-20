import datetime
from typing import Optional, List, TYPE_CHECKING

import strawberry
import strawberry_django

from superapp.apps.authentication.models import User


@strawberry_django.type(User, fields="__all__")
class UserType:
    email_verified: Optional[datetime.datetime]
    phone_verified: Optional[datetime.datetime]
    is_anonymous: bool
    

