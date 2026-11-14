"""An announcement's filters as pure functions, used to pick the phones a push goes to.

The website and the apps apply the same rules on the device (the list endpoint
sends the filters with each announcement). Every rule that is set must match;
an empty rule matches everyone.
"""

from ..utils.app_versions import parse_version, version_code  # noqa: F401  (re-exported)
from dataclasses import dataclass, field
from typing import Optional

WEB = 'web'
WEB_PLATFORMS = ('web_mobile', 'web_desktop')
APP_PLATFORMS = ('android', 'ios')


@dataclass(frozen=True)
class Audience:
    """One device: an AppUsers row for push, or a website visit (with its viewport)."""
    platform: str = ''
    viewport: str = ''
    country: str = ''
    locale: str = ''
    app_version: str = ''


@dataclass(frozen=True)
class TargetingRules:
    platforms: frozenset = field(default_factory=frozenset)
    countries_include: frozenset = field(default_factory=frozenset)
    countries_exclude: frozenset = field(default_factory=frozenset)
    locales: tuple = ()
    min_app_version: str = ''
    max_app_version: str = ''

    @classmethod
    def build(cls, *, platforms=(), countries_include=(), countries_exclude=(), locales=(),
              min_app_version='', max_app_version=''):
        """Normalized rules from raw admin lists (case and blanks are cleaned)."""
        return cls(
            platforms=frozenset(_clean(platforms, str.lower)),
            countries_include=frozenset(_clean(countries_include, str.upper)),
            countries_exclude=frozenset(_clean(countries_exclude, str.upper)),
            locales=tuple(_clean(locales, normalize_locale)),
            min_app_version=(min_app_version or '').strip(),
            max_app_version=(max_app_version or '').strip(),
        )


def _clean(values, transform=lambda value: value):
    return [transform(str(value).strip()) for value in (values or []) if str(value).strip()]


def normalize_locale(locale: str) -> str:
    """'ro_RO' -> 'ro-ro'."""
    return (locale or '').strip().replace('_', '-').lower()


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


def _app_version_matches(rules, audience) -> bool:
    if (audience.platform or '').lower() == WEB:
        return True
    if rules.min_app_version and compare_versions(audience.app_version, rules.min_app_version) not in (0, 1):
        return False
    if rules.max_app_version and compare_versions(audience.app_version, rules.max_app_version) not in (0, -1):
        return False
    return True
