"""Per-caller request budgets for the public write endpoints (Redis-backed)."""
from django_ratelimit.core import is_ratelimited


def over_limit(request, group: str, value: str, rate: str) -> bool:
    """Counts this request against `value`'s budget in `group`; True when spent.
    An empty `value` (no usable IP) shares one bucket instead of skipping the limit."""
    key = value or 'unknown'
    return is_ratelimited(request, group=group, key=lambda _group, _request: key, rate=rate, increment=True)
