"""scraper_engine: how reports are dated, the files it writes for the
other pod processes, and compatibility with a Django that predates the
song fields of the report response."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import scraper_engine as se  # noqa: E402

NOW = 1_800_000_000.0
ICY_A = se.IcySong("Artist A - Song A", NOW - 40)
ICY_B = se.IcySong("Artist B - Song B", NOW - 12)


class ReportClockTests(unittest.TestCase):
    def setUp(self):
        self.clock = se.ReportClock()
        # The first report has no earlier change to compare ICY with.
        first = self.clock.date("Artist A - Song A", ICY_A, NOW - 30)
        self.assertEqual(first, se.Dating(NOW - 30, True, None, False))

    def test_change_with_new_icy_song_is_dated_by_icy(self):
        dating = self.clock.date("Artist B - Song B", ICY_B, NOW)
        self.assertEqual(dating, se.Dating(ICY_B.started_at, True, ICY_B))

    def test_icy_dates_the_change_even_when_titles_differ(self):
        # The scrape formats the song differently (or lags ICY by a whole
        # interval): ICY changed since the last change, so its start wins.
        dating = self.clock.date("SONG B (Live) / Artist B", ICY_B, NOW)
        self.assertEqual(dating.timestamp, ICY_B.started_at)
        self.assertIs(dating.icy, ICY_B)
        self.assertFalse(dating.scrape_dated_change)

    def test_change_without_icy_change_is_dated_by_the_scrape(self):
        dating = self.clock.date("Artist C - Song C", ICY_A, NOW)
        self.assertEqual(dating, se.Dating(NOW, True, None, True))

    def test_unchanged_song_resends_its_change_timestamp(self):
        self.clock.date("Artist B - Song B", ICY_B, NOW)
        again = self.clock.date("Artist B - Song B", ICY_B, NOW + 30)
        self.assertEqual(again, se.Dating(ICY_B.started_at, False, ICY_B))
        # ICY moving on does not re-date a song the scrape still reports.
        later = se.IcySong("Artist C - Song C", NOW + 50)
        again = self.clock.date("Artist B - Song B", later, NOW + 60)
        self.assertEqual(again.timestamp, ICY_B.started_at)
        self.assertIs(again.icy, ICY_B)

    def test_icy_without_a_start_cannot_date(self):
        dating = self.clock.date("Artist B - Song B",
                                 se.IcySong("Artist B - Song B", 0.0), NOW)
        self.assertEqual(dating.timestamp, NOW)
        self.assertTrue(dating.scrape_dated_change)

    def test_icy_appearing_after_the_last_change_dates_the_next(self):
        clock = se.ReportClock()
        clock.date("Artist A - Song A", None, NOW - 60)
        dating = clock.date("Artist B - Song B", ICY_B, NOW)
        self.assertEqual(dating.timestamp, ICY_B.started_at)


class FakeDjango:
    """Records GraphQL calls; answers like the fixed Django."""

    def __init__(self, song_fields=True):
        self.song_fields = song_fields
        self.calls = []

    def __call__(self, query, variables=None):
        self.calls.append((query, variables))
        if "report_station_metadata" not in query:
            return {}, []
        if "song_title" in query and not self.song_fields:
            return {}, [{"message": "Cannot query field 'song_title' on "
                                    "type 'ReportStationMetadataResponse'."}]
        inp = variables["input"]
        response = {"success": True, "message": "ok", "song_id": 42,
                    "thumbnail_url": "https://source.example/raw.jpg"}
        if "song_title" in query:
            response.update({
                "song_title": (inp["song_title"] or "").title(),
                "song_artist": inp["song_artist"], "song_artist_id": 7,
                "song_thumbnail_url": "https://cdn.example/p/42.webp",
                "history_timestamp": "2027-01-15T08:00:00+00:00",
            })
        return {"report_station_metadata": response}, []

    def reports(self):
        return [v["input"] for q, v in self.calls
                if "report_station_metadata" in q]


class PodFilesFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.django = FakeDjango()
        self.events = []
        self.patches = [
            mock.patch.object(se, "METADATA_INDEX", root / "index.json"),
            mock.patch.object(se, "STATION_CONFIG_PATH",
                              root / "station.json"),
            mock.patch.object(se, "NOW_PLAYING_PATH",
                              root / "now_playing.json"),
            mock.patch.object(se, "_graphql_call", self.django),
            mock.patch.object(se, "_now_playing_key", None),
            mock.patch.object(se, "_song_fields_retry_at", 0.0),
            mock.patch.object(se, "_config", {
                "station_id": 1, "scrapers": [], "config_version": 3,
                "id3_metadata_delay_offset": 10}),
            mock.patch.object(se.posthog_reporter, "capture_event",
                              lambda e, p=None: self.events.append((e, p))),
        ]
        for p in self.patches:
            p.start()
        self.root = root

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def write_icy(self, icy):
        se.METADATA_INDEX.write_text(json.dumps({"current": {
            "raw": icy.raw, "started_at": icy.started_at},
            "recent": [], "monitor_alive_at": NOW}))

    def now_playing(self):
        return json.loads(se.NOW_PLAYING_PATH.read_text())


class ScraperModeTests(PodFilesFixture):
    def scrape(self, clock, raw, icy, now):
        self.write_icy(icy)
        result = {"raw_title": raw, "title": raw.split(" - ")[-1],
                  "artist": raw.split(" - ")[0], "dirty": False}
        with mock.patch.object(se, "_run_scrapers", return_value=result):
            se._scrape_and_report(clock, "scraper", now)

    def test_icy_dated_change_publishes_the_stored_song(self):
        clock = se.ReportClock()
        self.scrape(clock, "Artist A - Song A", ICY_A, NOW - 30)
        self.assertFalse(se.NOW_PLAYING_PATH.exists())
        self.scrape(clock, "Artist B - Song B", ICY_B, NOW)
        report = self.django.reports()[-1]
        self.assertEqual(datetime.fromisoformat(
            report["scraper_timestamp"]).timestamp(), ICY_B.started_at)
        self.assertEqual(self.now_playing(), {
            "raw": ICY_B.raw, "started_at": ICY_B.started_at,
            "title": "Song B", "artist": "Artist B", "song_id": 42,
            "song_artist_id": 7,
            "song_thumbnail_url": "https://cdn.example/p/42.webp",
            "history_timestamp": "2027-01-15T08:00:00+00:00",
            "reported_at": NOW,
        })

    def test_scrape_dated_change_withdraws_the_hint_and_is_counted(self):
        clock = se.ReportClock()
        self.scrape(clock, "Artist A - Song A", ICY_A, NOW - 60)
        self.scrape(clock, "Artist B - Song B", ICY_B, NOW - 30)
        self.assertTrue(se.NOW_PLAYING_PATH.exists())
        self.scrape(clock, "Artist C - Song C", ICY_B, NOW)
        self.assertFalse(se.NOW_PLAYING_PATH.exists())
        self.assertEqual(datetime.fromisoformat(
            self.django.reports()[-1]["scraper_timestamp"]).timestamp(), NOW)
        self.assertEqual(self.events, [("scrape_dated_song_change", {
            "timestamp_source": "scraper", "icy_known": True})])

    def test_index_json_is_never_written(self):
        # metadata_monitor is its single writer: the old read-modify-
        # write of song_id/thumbnail_url raced with it.
        self.write_icy(ICY_B)
        os.utime(se.METADATA_INDEX, (1_000_000_000, 1_000_000_000))
        before = se.METADATA_INDEX.read_bytes()
        clock = se.ReportClock()
        for raw, now in (("Artist A - Song A", NOW - 30),
                         ("Artist B - Song B", NOW)):
            with mock.patch.object(se, "_run_scrapers", return_value={
                    "raw_title": raw, "title": raw, "artist": ""}):
                se._scrape_and_report(clock, "scraper", now)
        se._report_icy_change(ICY_B, NOW)
        self.assertEqual(len(self.django.reports()), 3)
        self.assertEqual(se.METADATA_INDEX.read_bytes(), before)
        self.assertEqual(se.METADATA_INDEX.stat().st_mtime, 1_000_000_000)


class Id3ModeTests(PodFilesFixture):
    def test_change_is_dated_by_the_offset_corrected_icy_start(self):
        # metadata_monitor already subtracted the delay offset; the scraper
        # must not subtract it again.
        self.write_icy(ICY_B)
        se._report_icy_change(ICY_B, NOW)
        report = self.django.reports()[-1]
        self.assertEqual(report["timestamp_source"], "id3_metadata")
        self.assertEqual(datetime.fromisoformat(
            report["id3_timestamp"]).timestamp(), ICY_B.started_at)
        self.assertEqual(report["song_title"], "Song B")
        self.assertEqual(self.now_playing()["started_at"], ICY_B.started_at)

    def test_without_an_icy_start_the_detection_is_now_minus_offset(self):
        se._report_icy_change(se.IcySong("A - B", 0.0), NOW)
        report = self.django.reports()[-1]
        self.assertEqual(datetime.fromisoformat(
            report["id3_timestamp"]).timestamp(), NOW - 10)
        self.assertFalse(se.NOW_PLAYING_PATH.exists())


class StationConfigTests(PodFilesFixture):
    def test_station_json_follows_the_loaded_config(self):
        se._load_config({"config_version": 4, "id3_metadata_delay_offset": -10})
        self.assertEqual(json.loads(se.STATION_CONFIG_PATH.read_text()), {
            "id3_metadata_delay_offset": -10.0, "config_version": 4})
        se._load_config({"config_version": 5,
                         "id3_metadata_delay_offset": None})
        self.assertEqual(json.loads(se.STATION_CONFIG_PATH.read_text()), {
            "id3_metadata_delay_offset": 0.0, "config_version": 5})


class OlderDjangoTests(PodFilesFixture):
    def test_report_falls_back_to_the_legacy_selection(self):
        self.django.song_fields = False
        with mock.patch.object(se.time, "time", return_value=NOW):
            response = se._report_metadata("Song", "Artist", raw_title="x")
        self.assertTrue(response["success"])
        queries = [q for q, _ in self.django.calls]
        self.assertIn("song_title", queries[0])
        self.assertNotIn("song_title", queries[1])
        # Later reports skip the rejected fields until the retry interval.
        with mock.patch.object(se.time, "time", return_value=NOW + 60):
            se._report_metadata("Song", "Artist", raw_title="x")
        self.assertNotIn("song_title", self.django.calls[-1][0])
        self.django.song_fields = True
        later = NOW + se.SONG_FIELDS_RETRY_INTERVAL + 1
        with mock.patch.object(se.time, "time", return_value=later):
            response = se._report_metadata("Song", "Artist", raw_title="x")
        self.assertIn("song_title", self.django.calls[-1][0])
        self.assertEqual(response["song_thumbnail_url"],
                         "https://cdn.example/p/42.webp")

    def test_hint_without_song_fields_carries_only_the_song_id(self):
        self.django.song_fields = False
        self.write_icy(ICY_B)
        se._report_icy_change(ICY_B, NOW)
        np = self.now_playing()
        self.assertEqual(np["song_id"], 42)
        self.assertIsNone(np["title"])
        self.assertIsNone(np["song_thumbnail_url"])


class ScrapedTitleHygieneTests(unittest.TestCase):
    def test_placeholders_and_decoder_messages_are_not_reported(self):
        cfg = [{"category_slug": "icecast", "url": "http://x", "priority": 1}]
        for bad in ("-", "N/A", "ChannelElement 3.1 missing", "  "):
            with mock.patch.dict(se.SCRAPERS, {
                    "icecast": lambda url, bad=bad: {"raw_title": bad}}):
                self.assertEqual(se._run_scrapers(cfg), {})
        with mock.patch.dict(se.SCRAPERS, {
                "icecast": lambda url: {"raw_title": " A  -  B "}}):
            self.assertEqual(se._run_scrapers(cfg)["raw_title"], "A - B")


if __name__ == "__main__":
    unittest.main()
