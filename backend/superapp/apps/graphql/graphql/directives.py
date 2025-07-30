from __future__ import annotations

import strawberry
from graphql import DirectiveLocation
from typing import Optional

@strawberry.directive(
    locations=[DirectiveLocation.QUERY, DirectiveLocation.MUTATION],
    description="Cache directive for Hasura compatibility and query-level caching",
)
class cached:
    ttl: Optional[int] = strawberry.directive_field(name="ttl", default=60)
    refresh: Optional[bool] = strawberry.directive_field(name="refresh", default=False)

@strawberry.directive(
    locations=[
        DirectiveLocation.FIELD_DEFINITION, 
        DirectiveLocation.QUERY, 
        DirectiveLocation.MUTATION
    ],
    description="Cache control configuration for QueryCache extension",
)
class cache_control:
    max_age: Optional[int] = strawberry.directive_field(name="max_age", default=300)
    stale_while_revalidate: Optional[int] = strawberry.directive_field(name="stale_while_revalidate", default=60)
    no_cache: Optional[bool] = strawberry.directive_field(name="no_cache", default=False)
    private: Optional[bool] = strawberry.directive_field(name="private", default=False)
    vary_by_user: Optional[bool] = strawberry.directive_field(name="vary_by_user", default=False)
    vary_by_args: Optional[bool] = strawberry.directive_field(name="vary_by_args", default=True)