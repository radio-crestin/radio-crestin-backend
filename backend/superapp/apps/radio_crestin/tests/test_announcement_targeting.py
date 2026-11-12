from django.test import SimpleTestCase

from ..services.announcement_targeting import (
    Audience, TargetingRules, compare_versions, matches, parse_version,
)


def rules(**kwargs):
    return TargetingRules.build(**kwargs)


class EmptyRulesTests(SimpleTestCase):
    def test_empty_rules_match_everyone(self):
        self.assertTrue(matches(rules(), Audience()))
        self.assertTrue(matches(rules(), Audience(platform='android', country='DE', locale='hu')))


class PlatformTests(SimpleTestCase):
    def test_app_platforms(self):
        android_only = rules(platforms=['android'])
        self.assertTrue(matches(android_only, Audience(platform='android')))
        self.assertTrue(matches(android_only, Audience(platform='Android')))
        self.assertFalse(matches(android_only, Audience(platform='ios')))
        self.assertFalse(matches(android_only, Audience(platform='web')))
        self.assertFalse(matches(android_only, Audience()))

    def test_website_viewport_picks_the_web_value(self):
        phones = rules(platforms=['web_mobile'])
        self.assertTrue(matches(phones, Audience(platform='web', viewport='mobile')))
        self.assertFalse(matches(phones, Audience(platform='web', viewport='desktop')))

    def test_website_without_viewport_matches_either_web_value(self):
        self.assertTrue(matches(rules(platforms=['web_mobile']), Audience(platform='web')))
        self.assertTrue(matches(rules(platforms=['web_desktop']), Audience(platform='web')))
        self.assertFalse(matches(rules(platforms=['ios']), Audience(platform='web')))


class CountryTests(SimpleTestCase):
    def test_include(self):
        only_ro_md = rules(countries_include=['ro', 'MD'])
        self.assertTrue(matches(only_ro_md, Audience(country='RO')))
        self.assertTrue(matches(only_ro_md, Audience(country='md')))
        self.assertFalse(matches(only_ro_md, Audience(country='DE')))
        self.assertFalse(matches(only_ro_md, Audience()))

    def test_exclude(self):
        not_de = rules(countries_exclude=['DE'])
        self.assertFalse(matches(not_de, Audience(country='DE')))
        self.assertTrue(matches(not_de, Audience(country='RO')))
        self.assertTrue(matches(not_de, Audience()))


class LocaleTests(SimpleTestCase):
    def test_language_prefix(self):
        romanian = rules(locales=['ro'])
        for locale in ('ro', 'ro-RO', 'ro_RO', 'RO-md'):
            self.assertTrue(matches(romanian, Audience(locale=locale)), locale)
        for locale in ('rom', 'en-RO', '', 'hu'):
            self.assertFalse(matches(romanian, Audience(locale=locale)), locale)

    def test_full_locale_rule(self):
        self.assertTrue(matches(rules(locales=['ro_RO']), Audience(locale='ro-RO')))
        self.assertFalse(matches(rules(locales=['ro-RO']), Audience(locale='ro-MD')))


class AppVersionTests(SimpleTestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version('1.6.2'), (1, 6, 2))
        self.assertEqual(parse_version('v1.6'), (1, 6, 0))
        self.assertEqual(parse_version('1.6.2+56'), (1, 6, 2))
        self.assertEqual(parse_version('1.10.0-beta'), (1, 10, 0))
        self.assertIsNone(parse_version(''))
        self.assertIsNone(parse_version('beta'))

    def test_compare_is_semantic_not_lexical(self):
        self.assertEqual(compare_versions('1.10.0', '1.9.9'), 1)
        self.assertEqual(compare_versions('1.6', '1.6.0'), 0)
        self.assertEqual(compare_versions('1.6.0.1', '1.6'), 1)
        self.assertIsNone(compare_versions('x', '1.0'))

    def test_min_and_max(self):
        below_1_6 = rules(max_app_version='1.5.99')
        self.assertTrue(matches(below_1_6, Audience(platform='android', app_version='1.5.2')))
        self.assertFalse(matches(below_1_6, Audience(platform='android', app_version='1.6.0')))

        window = rules(min_app_version='1.6.0', max_app_version='1.7.0')
        self.assertTrue(matches(window, Audience(platform='ios', app_version='1.6.0')))
        self.assertTrue(matches(window, Audience(platform='ios', app_version='1.7.0')))
        self.assertFalse(matches(window, Audience(platform='ios', app_version='1.10.0')))
        self.assertFalse(matches(window, Audience(platform='ios', app_version='')))

    def test_ignored_for_web(self):
        self.assertTrue(matches(rules(min_app_version='9.0'), Audience(platform='web')))


class CombinedRulesTests(SimpleTestCase):
    def test_all_set_rules_must_match(self):
        romanians_in_germany = rules(countries_include=['DE'], locales=['ro'])
        self.assertTrue(matches(romanians_in_germany, Audience(country='DE', locale='ro-RO')))
        self.assertFalse(matches(romanians_in_germany, Audience(country='DE', locale='de-DE')))
        self.assertFalse(matches(romanians_in_germany, Audience(country='RO', locale='ro-RO')))
