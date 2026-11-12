"""Who sees an announcement: pure functions shared by the list endpoint and push sending.

Every rule that is set must match; an empty rule matches everyone.
"""
import ipaddress
import re
from dataclasses import dataclass, field
from typing import Optional

WEB = 'web'
WEB_PLATFORMS = ('web_mobile', 'web_desktop')
APP_PLATFORMS = ('android', 'ios')


@dataclass(frozen=True)
class Audience:
    """The device asking: from the request (list endpoint) or an AppUsers row (push)."""
    platform: str = ''
    viewport: str = ''
    country: str = ''
    locale: str = ''
    device_id: str = ''
    ip: str = ''
    app_version: str = ''


@dataclass(frozen=True)
class TargetingRules:
    platforms: frozenset = field(default_factory=frozenset)
    countries_include: frozenset = field(default_factory=frozenset)
    countries_exclude: frozenset = field(default_factory=frozenset)
    locales: tuple = ()
    device_ids: frozenset = field(default_factory=frozenset)
    ip_ranges: tuple = ()
    has_ip_rule: bool = False  # True even when every entry was invalid: then nobody matches.
    min_app_version: str = ''
    max_app_version: str = ''

    @classmethod
    def build(cls, *, platforms=(), countries_include=(), countries_exclude=(), locales=(),
              device_ids=(), ip_ranges=(), min_app_version='', max_app_version=''):
        """Normalized rules from raw admin lists (case, blanks and invalid IP ranges are cleaned)."""
        return cls(
            platforms=frozenset(_clean(platforms, str.lower)),
            countries_include=frozenset(_clean(countries_include, str.upper)),
            countries_exclude=frozenset(_clean(countries_exclude, str.upper)),
            locales=tuple(_clean(locales, normalize_locale)),
            device_ids=frozenset(_clean(device_ids)),
            ip_ranges=tuple(parse_ip_ranges(ip_ranges)),
            has_ip_rule=bool(_clean(ip_ranges)),
            min_app_version=(min_app_version or '').strip(),
            max_app_version=(max_app_version or '').strip(),
        )


def _clean(values, transform=lambda value: value):
    return [transform(str(value).strip()) for value in (values or []) if str(value).strip()]


def normalize_locale(locale: str) -> str:
    """'ro_RO' -> 'ro-ro'."""
    return (locale or '').strip().replace('_', '-').lower()


def parse_ip_ranges(values):
    """IP networks from 'IP' or 'CIDR' strings; invalid entries are dropped."""
    networks = []
    for value in values or []:
        try:
            networks.append(ipaddress.ip_network(str(value).strip(), strict=False))
        except ValueError:
            continue
    return networks


def parse_version(version: str) -> Optional[tuple]:
    """'1.6.2', 'v1.6', '1.6.2+56' or '1.6.2-beta' -> (1, 6, 2); None when unparseable."""
    match = re.match(r'^\s*v?(\d+(?:\.\d+)*)', version or '')
    if not match:
        return None
    parts = [int(part) for part in match.group(1).split('.')]
    return tuple(parts + [0] * (3 - len(parts)))


def compare_versions(left: str, right: str) -> Optional[int]:
    """-1, 0 or 1; None when either side is unparseable."""
    a, b = parse_version(left), parse_version(right)
    if a is None or b is None:
        return None
    width = max(len(a), len(b))
    a, b = a + (0,) * (width - len(a)), b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def matches(rules: TargetingRules, audience: Audience) -> bool:
    return (
        _platform_matches(rules.platforms, audience)
        and _country_matches(rules, audience.country)
        and _locale_matches(rules.locales, audience.locale)
        and _device_matches(rules.device_ids, audience.device_id)
        and _ip_matches(rules, audience.ip)
        and _app_version_matches(rules, audience)
    )


def audience_platform_values(audience: Audience) -> set:
    """The rule values this device matches: a website without viewport matches both web values."""
    platform = (audience.platform or '').lower()
    if platform == WEB:
        viewport = (audience.viewport or '').lower()
        if viewport in ('mobile', 'desktop'):
            return {f'web_{viewport}'}
        return set(WEB_PLATFORMS)
    return {platform} if platform else set()


def _platform_matches(platforms, audience) -> bool:
    return not platforms or bool(platforms & audience_platform_values(audience))


def _country_matches(rules, country) -> bool:
    country = (country or '').upper()
    if rules.countries_include and country not in rules.countries_include:
        return False
    return country not in rules.countries_exclude


def _locale_matches(locales, locale) -> bool:
    if not locales:
        return True
    locale = normalize_locale(locale)
    return bool(locale) and any(locale == rule or locale.startswith(rule + '-') for rule in locales)


def _device_matches(device_ids, device_id) -> bool:
    return not device_ids or (device_id or '') in device_ids


def _ip_matches(rules, ip) -> bool:
    if not rules.has_ip_rule:
        return True
    try:
        address = ipaddress.ip_address((ip or '').strip())
    except ValueError:
        return False
    return any(address.version == network.version and address in network for network in rules.ip_ranges)


def _app_version_matches(rules, audience) -> bool:
    if (audience.platform or '').lower() == WEB:
        return True
    if rules.min_app_version and compare_versions(audience.app_version, rules.min_app_version) not in (0, 1):
        return False
    if rules.max_app_version and compare_versions(audience.app_version, rules.max_app_version) not in (0, -1):
        return False
    return True
