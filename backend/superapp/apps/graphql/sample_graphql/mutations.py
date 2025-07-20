from __future__ import annotations

import functools
from typing import TYPE_CHECKING

import strawberry

from strawberry_django.resolvers import django_resolver

try:
    # Django-channels is not always used/intalled,
    # therefore it shouldn't be it a hard requirement.
    from channels import auth as channels_auth
except ModuleNotFoundError:
    channels_auth = None

if TYPE_CHECKING:
    from strawberry.types import Info


@django_resolver
def resolve_sample_mutation(info: Info, sample_input: str) -> str:
    return f"sample mutation response here for input: {sample_input}"


@strawberry.type
class Mutation:
    sample_mutation: str = functools.partial(strawberry.mutation, resolver=resolve_sample_mutation)()
