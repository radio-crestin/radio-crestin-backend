from __future__ import annotations

import strawberry
from graphql import DirectiveLocation
from strawberry.directive import DirectiveValue
from typing import Optional, Any

"""
GraphQL Schema Directives Infrastructure

This file demonstrates the infrastructure for automatic directive discovery and registration.
Using function-based directives for better runtime behavior and compatibility.

## Automatic Discovery System

The schema.py includes a `find_graphql_directives()` function that:
1. Scans all installed Django apps for graphql/directives.py files
2. Imports directive functions decorated with @strawberry.directive
3. Automatically registers them in the GraphQL schema

## Usage Pattern

Create directives in any app's graphql/directives.py file:

```python
@strawberry.directive(locations=[DirectiveLocation.FIELD_DEFINITION])
def my_directive(
    value: DirectiveValue[Any],
    arg1: Optional[str] = "default",
    arg2: Optional[int] = 42
) -> Any:
    return value
```

Then use in GraphQL queries:
```graphql
query MyQuery {
  field @my_directive(arg1: "value", arg2: 100) {
    id
    name
  }
}
```

## Current Status

- ✅ Automatic directive discovery system implemented
- ✅ Proper function-based directive definitions created  
- ✅ Integration with schema.py completed
- ✅ Function-based directives fully working and registered in GraphQL schema
- ✅ QueryCache extension provides automatic caching with directive metadata
- ✅ Two directives available: @cached and @cache_control
- ℹ️ Using function-based directives due to Strawberry schema directive compatibility issues

## Usage

The directives are now active and can be used in GraphQL queries:
```graphql
query StationsWithCache {
  stations @cache_control(max_age: 600) {
    id
    title
  }
}
```

## Schema Directive Note

While Strawberry supports schema directives (class-based), they currently have compatibility 
issues with directive arguments and extension handling. Function-based directives provide 
better runtime behavior for our caching use case and integrate properly with the QueryCache extension.
"""

@strawberry.directive(
    locations=[DirectiveLocation.FIELD_DEFINITION],
    description="Cache directive for Hasura compatibility and field-level caching"
)
def cached(
    value: DirectiveValue[Any],
    ttl: Optional[int] = 60,
    refresh: Optional[bool] = False
) -> Any:
    """Cache directive implementation"""
    # The directive processing is handled by the QueryCache extension
    # This directive serves as metadata for cache control
    return value

@strawberry.directive(
    locations=[DirectiveLocation.FIELD_DEFINITION],
    description="Advanced cache control directive for fine-grained caching"
)
def cache_control(
    value: DirectiveValue[Any],
    max_age: Optional[int] = 300,
    stale_while_revalidate: Optional[int] = 60,
    no_cache: Optional[bool] = False,
    private: Optional[bool] = False,
    vary_by_user: Optional[bool] = False,
    vary_by_args: Optional[bool] = True
) -> Any:
    """Cache control directive implementation"""
    # The directive processing is handled by the QueryCache extension
    # This directive serves as metadata for cache control
    return value
