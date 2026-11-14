"""Per-caller request budgets for the public write endpoints (Redis-backed)."""
from django_ratelimit.core import is_ratelimited


def over_limit(request, group: str, value: str, rate: str) -> bool:
    """Counts this request against `value`'s budget in `group`; True when spent.
    A caller with no `value` (no usable address) is refused rather than put in
    a bucket it would share with every other such caller."""
    if not value:
        return True
    return is_ratelimited(request, group=group, key=lambda _group, _request: value, rate=rate, increment=True)
