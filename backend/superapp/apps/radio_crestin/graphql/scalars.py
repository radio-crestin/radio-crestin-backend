from __future__ import annotations

import strawberry
from datetime import datetime
from typing import NewType, Any

# Define timestamptz scalar for Hasura compatibility
@strawberry.scalar(
    serialize=lambda v: v.isoformat() if v else None,
    parse_value=lambda v: datetime.fromisoformat(v.replace('Z', '+00:00')) if v else None,
)
class timestamptz(datetime):
    """
    Timestamp with timezone scalar type for Hasura compatibility.
    Handles ISO format datetime strings with timezone information.
    """
    pass

# JSON scalar for Hasura compatibility  
@strawberry.scalar(
    serialize=lambda v: v,
    parse_value=lambda v: v,
)
class jsonb:
    """
    JSONB scalar type for Hasura compatibility.
    Allows arbitrary JSON data to be stored and retrieved.
    """
    pass