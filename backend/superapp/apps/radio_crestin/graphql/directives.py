from __future__ import annotations

import strawberry
from strawberry.directive import Location
from typing import Optional

@strawberry.directive(
    locations=[Location.QUERY],
    description="whether this query should be cached (Hasura Cloud only)",
)
class cached:
    ttl: Optional[int] = strawberry.directive_field(
        default=60,
        description="measured in seconds"
    )
    refresh: Optional[bool] = strawberry.directive_field(
        default=False,
        description="refresh the cache entry"
    )