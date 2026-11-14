"""Config reloads: scraper_engine fetches its config when the config_version
Django gave health_server is newer than the loaded one, and every
CONFIG_POLL_INTERVAL otherwise, instead of every minute."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import health_server as hs  # noqa: E402
import scraper_engine as se  # noqa: E402

T = 1_800_000_000.0


class ConfigPollTests(unittest.TestCase):
    def setUp(self):
        self.poll = se.ConfigPoll(T)

    def test_nothing_new_waits_for_the_interval(self):
        self.assertFalse(self.poll.due(3, 3, T + 60))
        self.assertFalse(self.poll.due(3, 0, T + se.CONFIG_POLL_INTERVAL))
        self.assertTrue(self.poll.due(3, 3, T + se.CONFIG_POLL_INTERVAL + 1))

    def test_a_newer_version_is_fetched_at_once(self):
        self.assertTrue(self.poll.due(3, 4, T + 5))

    def test_a_version_is_fetched_once_even_when_the_fetch_fails(self):
        self.poll.fetched(4, T + 5)
        # the fetch failed: still on v3, but v4 is not asked for again
        self.assertFalse(self.poll.due(3, 4, T + 7))
        self.assertTrue(self.poll.due(3, 5, T + 70))
        self.assertTrue(self.poll.due(3, 4, T + 5 + se.CONFIG_POLL_INTERVAL + 1))


class LatestConfigVersionFileTests(unittest.TestCase):
    """health_server writes the version, scraper_engine reads it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "metadata" / "latest_config_version"
        self.patches = [
            mock.patch.object(hs, "LATEST_CONFIG_VERSION", str(path)),
            mock.patch.object(se, "LATEST_CONFIG_VERSION", path),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_round_trip(self):
        self.assertEqual(se._latest_config_version(), 0)
        hs.write_latest_config_version(7)
        self.assertEqual(se._latest_config_version(), 7)

    def test_a_django_without_the_version_leaves_the_file_alone(self):
        hs.write_latest_config_version(7)
        for missing in (None, "8", True):
            hs.write_latest_config_version(missing)
        self.assertEqual(se._latest_config_version(), 7)

    def test_the_report_passes_the_version_on(self):
        answer = {"success": True, "config_version": 9}
        with mock.patch("django_api_client.report_health", return_value=answer):
            self.assertTrue(hs._report_to_django(True, 0, "ok"))
        self.assertEqual(se._latest_config_version(), 9)

    def test_an_old_django_answer_still_counts_as_accepted(self):
        with mock.patch("django_api_client.report_health",
                        return_value={"success": True}):
            self.assertTrue(hs._report_to_django(True, 0, "ok"))
        self.assertEqual(se._latest_config_version(), 0)


if __name__ == "__main__":
    unittest.main()
