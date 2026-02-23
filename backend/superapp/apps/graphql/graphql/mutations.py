import functools
import strawberry
from strawberry.types import Info

from strawberry_django.resolvers import django_resolver

try:
    # Django-channels is not always used/intalled,
    # therefore it shouldn't be it a hard requirement.
    from channels import auth as channels_auth
except ModuleNotFoundError:
    channels_auth = None


@django_resolver
def check_health(info: Info) -> bool:
    return True


@strawberry.type
class Mutation:
    check_health: str = functools.partial(strawberry.mutation, resolver=check_health)()
