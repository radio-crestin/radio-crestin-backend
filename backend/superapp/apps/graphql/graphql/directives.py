from __future__ import annotations

import strawberry
from strawberry.directive import DirectiveLocation
from typing import Optional


@strawberry.directive(
    locations=[
        # DirectiveLocation.FIELD,
        DirectiveLocation.QUERY,
        DirectiveLocation.MUTATION,
    ],
    description="Cache directive for field-level caching and query/mutation result caching"
)
def cached(
    ttl: Optional[int] = 60,
    refresh_while_caching: Optional[bool] = True
):
    """Cache directive for field-level caching"""
    def decorator(resolver):
        # Store directive parameters in resolver metadata for caching extension
        resolver._cached_metadata = {"ttl": ttl, "refresh_while_caching": refresh_while_caching}
        return resolver
    return decorator


@strawberry.directive(
    locations=[DirectiveLocation.QUERY, DirectiveLocation.MUTATION],
    description="Cache control directive for HTTP cache headers"
)
def cache_control(
    max_age: Optional[int] = 300,
    stale_while_revalidate: Optional[int] = None,
    max_stale: Optional[int] = None,
    public: Optional[bool] = None,
    private: Optional[bool] = None,
    no_cache: Optional[bool] = False,
    immutable: Optional[bool] = None
):
    """Cache control directive for HTTP cache headers"""
    def decorator(resolver):
        # Store directive parameters in resolver metadata for caching extension
        resolver._cache_control_metadata = {
            "max_age": max_age,
            "stale_while_revalidate": stale_while_revalidate,
            "max_stale": max_stale,
            "public": public,
            "private": private,
            "no_cache": no_cache,
            "immutable": immutable,
        }
        return resolver
    return decorator
