from __future__ import annotations
from typing import Optional

import strawberry
import strawberry_django
from strawberry_django.auth.utils import get_current_user

from ...authentication.graphql.types import UserType


def resolve_current_user(info) -> Optional[UserType]:
    """Resolve current user, returning None for anonymous users."""
    user = get_current_user(info)
    if user and user.is_authenticated:
        return user
    return None


@strawberry.type
class Query:

    current_user: Optional[UserType] = strawberry_django.field(
        description="Get the currently authenticated user, or null if anonymous",
        resolver=resolve_current_user
    )


