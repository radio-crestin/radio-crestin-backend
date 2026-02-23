import strawberry
from typing import Optional, List
from datetime import datetime

# Boolean comparison expressions (Hasura-style)
@strawberry.input
class Boolean_comparison_exp:
    _eq: Optional[bool] = None
    _neq: Optional[bool] = None
    _gt: Optional[bool] = None
    _gte: Optional[bool] = None
    _lt: Optional[bool] = None
    _lte: Optional[bool] = None
    _in: Optional[List[bool]] = None
    _nin: Optional[List[bool]] = None
    _is_null: Optional[bool] = None

# Integer comparison expressions
@strawberry.input
class Int_comparison_exp:
    _eq: Optional[int] = None
    _neq: Optional[int] = None
    _gt: Optional[int] = None
    _gte: Optional[int] = None
    _lt: Optional[int] = None
    _lte: Optional[int] = None
    _in: Optional[List[int]] = None
    _nin: Optional[List[int]] = None
    _is_null: Optional[bool] = None

# String comparison expressions 
@strawberry.input
class String_comparison_exp:
    _eq: Optional[str] = None
    _neq: Optional[str] = None
    _gt: Optional[str] = None
    _gte: Optional[str] = None
    _lt: Optional[str] = None
    _lte: Optional[str] = None
    _in: Optional[List[str]] = None
    _nin: Optional[List[str]] = None
    _is_null: Optional[bool] = None
    _like: Optional[str] = None
    _nlike: Optional[str] = None
    _ilike: Optional[str] = None
    _nilike: Optional[str] = None

# Timestamp comparison expressions
@strawberry.input
class timestamptz_comparison_exp:
    _eq: Optional[datetime] = None
    _neq: Optional[datetime] = None
    _gt: Optional[datetime] = None
    _gte: Optional[datetime] = None
    _lt: Optional[datetime] = None
    _lte: Optional[datetime] = None
    _in: Optional[List[datetime]] = None
    _nin: Optional[List[datetime]] = None
    _is_null: Optional[bool] = None

# Ordering enums
from enum import Enum

class OrderByEnum(Enum):
    asc = "asc"
    asc_nulls_first = "asc_nulls_first"
    asc_nulls_last = "asc_nulls_last"
    desc = "desc"
    desc_nulls_first = "desc_nulls_first"
    desc_nulls_last = "desc_nulls_last"

order_by = strawberry.enum(OrderByEnum)

# Station ordering
@strawberry.input
class stations_order_by:
    id: Optional[order_by] = None
    title: Optional[order_by] = None
    slug: Optional[order_by] = None
    email: Optional[order_by] = None
    website: Optional[order_by] = None
    description: Optional[order_by] = None
    stream_url: Optional[order_by] = None
    thumbnail: Optional[order_by] = None
    thumbnail_url: Optional[order_by] = None
    rss_feed: Optional[order_by] = None
    order: Optional[order_by] = None
    feature_latest_post: Optional[order_by] = None
    facebook_page_id: Optional[order_by] = None
    description_action_title: Optional[order_by] = None
    description_link: Optional[order_by] = None
    generate_hls_stream: Optional[order_by] = None
    created_at: Optional[order_by] = None
    updated_at: Optional[order_by] = None
    disabled: Optional[order_by] = None

# Station boolean expressions
@strawberry.input 
class stations_bool_exp:
    _and: Optional[List['stations_bool_exp']] = None
    _not: Optional['stations_bool_exp'] = None
    _or: Optional[List['stations_bool_exp']] = None
    id: Optional[Int_comparison_exp] = None
    title: Optional[String_comparison_exp] = None
    slug: Optional[String_comparison_exp] = None
    email: Optional[String_comparison_exp] = None
    website: Optional[String_comparison_exp] = None
    description: Optional[String_comparison_exp] = None
    stream_url: Optional[String_comparison_exp] = None
    thumbnail: Optional[String_comparison_exp] = None
    thumbnail_url: Optional[String_comparison_exp] = None
    rss_feed: Optional[String_comparison_exp] = None
    order: Optional[Int_comparison_exp] = None
    feature_latest_post: Optional[Boolean_comparison_exp] = None
    facebook_page_id: Optional[String_comparison_exp] = None
    description_action_title: Optional[String_comparison_exp] = None
    description_link: Optional[String_comparison_exp] = None
    generate_hls_stream: Optional[Boolean_comparison_exp] = None
    created_at: Optional[timestamptz_comparison_exp] = None
    updated_at: Optional[timestamptz_comparison_exp] = None
    disabled: Optional[Boolean_comparison_exp] = None