from __future__ import annotations

import strawberry
from graphql import DirectiveLocation
from typing import Optional

@strawberry.directive(
    locations=[DirectiveLocation.QUERY, DirectiveLocation.MUTATION],
    description="Cache directive for Hasura compatibility and query-level caching",
)
class cached:
    ttl: Optional[int] = 60
    refresh: Optional[bool] = False

@strawberry.directive(
    locations=[
        DirectiveLocation.FIELD_DEFINITION, 
        DirectiveLocation.QUERY, 
        DirectiveLocation.MUTATION
    ],
    description="Cache control configuration for QueryCache extension",
)
class cache_control:
    max_age: Optional[int] = 300
    stale_while_revalidate: Optional[int] = 60
    no_cache: Optional[bool] = False
    private: Optional[bool] = False
    vary_by_user: Optional[bool] = False  # Cache varies by authenticated user
    vary_by_args: Optional[bool] = True   # Cache varies by query arguments