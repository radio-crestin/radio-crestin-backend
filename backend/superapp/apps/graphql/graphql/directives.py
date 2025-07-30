from __future__ import annotations

import strawberry
from strawberry.directive import DirectiveLocation
from typing import Optional


@strawberry.directive(
    locations=[DirectiveLocation.FIELD],
    description="Cache directive for field-level caching"
)
def cached(
    value,
    ttl: Optional[int] = 60,
    refresh_while_caching: Optional[bool] = True
):
    """Cache directive for field-level caching"""
    # Store directive parameters in field metadata for caching extension
    if hasattr(value, '_cached_metadata'):
        value._cached_metadata = {"ttl": ttl, "refresh_while_caching": refresh_while_caching}
    return value


@strawberry.directive(
    locations=[DirectiveLocation.QUERY, DirectiveLocation.MUTATION],
    description="Cache control directive for HTTP cache headers"
)
def cache_control(
    value,
    max_age: Optional[int] = 300,
    stale_while_revalidate: Optional[int] = None,
    max_stale: Optional[int] = None,
    public: Optional[bool] = None,
    private: Optional[bool] = None,
    no_cache: Optional[bool] = False,
    immutable: Optional[bool] = None
):
    """Cache control directive for HTTP cache headers"""
    # Store directive parameters in result metadata for caching extension
    if hasattr(value, '_cache_control_metadata'):
        value._cache_control_metadata = {
            "max_age": max_age,
            "stale_while_revalidate": stale_while_revalidate,
            "max_stale": max_stale,
            "public": public,
            "private": private,
            "no_cache": no_cache,
            "immutable": immutable,
        }
    return value
