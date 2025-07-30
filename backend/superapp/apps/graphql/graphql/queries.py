from __future__ import annotations

from strawberry.exceptions.exception import StrawberryException
from typing import TYPE_CHECKING
import strawberry

try:
    # Django-channels is not always used/intalled,
    # therefore it shouldn't be it a hard requirement.
    from channels import auth as channels_auth
except ModuleNotFoundError:
    channels_auth = None

if TYPE_CHECKING:
    from strawberry.types import Info


@strawberry.type
class Query:
    @strawberry.field
    def health(self, info: strawberry.Info) -> bool:
        return True
