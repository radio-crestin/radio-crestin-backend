import datetime
from typing import Optional, List, TYPE_CHECKING

import strawberry
import strawberry_django

from superapp.apps.authentication.models import User


# Everything but the password hash.
@strawberry_django.type(User, exclude=["password"])
class UserType:
    email_verified: Optional[datetime.datetime]
    phone_verified: Optional[datetime.datetime]
    is_anonymous: bool
    

