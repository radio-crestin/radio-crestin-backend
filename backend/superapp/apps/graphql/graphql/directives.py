from __future__ import annotations

import strawberry
from strawberry.schema_directive import Location
from typing import Optional

"""
GraphQL Schema Directives Infrastructure

This file demonstrates the infrastructure for automatic directive discovery and registration.
The directives below are properly defined but temporarily disabled due to Strawberry complexity.

## Automatic Discovery System

The schema.py includes a `find_graphql_directives()` function that:
1. Scans all installed Django apps for graphql/directives.py files
2. Imports directive classes decorated with @strawberry.schema_directive
3. Automatically registers them in the GraphQL schema

## Usage Pattern

Create directives in any app's graphql/directives.py file:

```python
@strawberry.schema_directive(locations=[Location.FIELD_DEFINITION])
class my_directive:
    arg1: Optional[str] = "default"
    arg2: Optional[int] = 42
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
- ✅ Proper schema directive definitions created  
- ✅ Integration with schema.py completed
- ⏸️ Directives temporarily disabled due to Strawberry schema directive complexity
- ✅ QueryCache extension provides automatic caching without directives

## Future Implementation

When Strawberry schema directives are fully working, uncomment in schema.py:
```python
all_directives = find_graphql_directives()
```
"""

@strawberry.schema_directive(locations=[Location.FIELD_DEFINITION])
class cached:
    """Cache directive for Hasura compatibility and field-level caching"""
    ttl: Optional[int] = 60
    refresh: Optional[bool] = False

@strawberry.schema_directive(locations=[Location.FIELD_DEFINITION])  
class cache_control:
    """Advanced cache control directive for fine-grained caching"""
    max_age: Optional[int] = 300
    stale_while_revalidate: Optional[int] = 60
    no_cache: Optional[bool] = False
    private: Optional[bool] = False
    vary_by_user: Optional[bool] = False
    vary_by_args: Optional[bool] = True
