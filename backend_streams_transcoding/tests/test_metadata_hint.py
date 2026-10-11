"""EXT-X-RC-METADATA-CHANGED carries the current song as optional X-* hints
without breaking the EPOCH parser of app versions in the field.

The hints are the song as Django stored it, so they must equal what the API
returns for that song: the proxied thumbnail (`song_thumbnail_url`), never
the raw source URL, and the artist id when Django returns one.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import playlist_rewriter as pr  # noqa: E402

RAW = ("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n"
       "#EXT-X-MEDIA-SEQUENCE:1\n#EXTINF:6.0,\na.ts\n")
CURRENT = {"raw": "Artist - Song", "title": "Song", "artist": "Artist",
           "started_at": 1_800_000_123.25}
PROXIED = "https://cdn.example.com/proxy/a.webp?width=250&format=webp"
REPORTED = {"raw": "Artist - Song", "started_at": 1_800_000_123.25,
            "title": "Song", "artist": "Artist", "song_id": 42,
            "song_artist_id": 7, "song_thumbnail_url": PROXIED,
            "history_timestamp": "2027-01-15T08:02:03.250000+00:00",
            "reported_at": 1_800_000_125.0}


def rc_line(out):
    return next(line for line in out.splitlines()
                if line.startswith("#EXT-X-RC-METADATA-CHANGED:"))


def attributes(line):
    """RFC 8216 attribute list of a tag line (quoted values may hold
    commas)."""
    body = line.split(":", 1)[1]
    return dict(re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', body))


class MetadataHintTests(unittest.TestCase):
    def test_hints_follow_epoch(self):
        line = rc_line(pr.enhance(RAW, [CURRENT], REPORTED))
        self.assertEqual(
            line,
            '#EXT-X-RC-METADATA-CHANGED:STARTED-AT="2027-01-15T08:02:03.000Z",'
            'EPOCH=1800000123,X-TITLE="Song",X-ARTIST="Artist",'
            'X-SONG-ID="42",X-ARTIST-ID="7",'
            f'X-THUMBNAIL-URL="{PROXIED}"')

    def test_field_app_regex_still_reads_the_epoch(self):
        reported = dict(REPORTED, title='EPOCH=1 "live", part 2\nnext')
        line = rc_line(pr.enhance(RAW, [CURRENT], reported))
        self.assertEqual(re.search(r"EPOCH=(\d+)", line).group(1),
                         "1800000123")
        self.assertEqual(attributes(line)["X-TITLE"],
                         "\"EPOCH=1 'live', part 2 next\"")

    def test_no_hints_for_another_song_instance(self):
        for reported in (dict(REPORTED, started_at=1_800_000_000.0),
                         dict(REPORTED, raw="Other - Song"), None):
            line = rc_line(pr.enhance(RAW, [CURRENT], reported))
            self.assertNotIn(",X-", line)

    def test_raw_source_thumbnail_is_never_a_hint(self):
        # An older Django returns only the raw `thumbnail_url`; the API
        # serves the proxied one, so the hint leaves the image out.
        reported = {k: v for k, v in REPORTED.items()
                    if k not in ("song_thumbnail_url", "song_artist_id")}
        reported["thumbnail_url"] = "https://source.example/raw.jpg"
        attrs = attributes(rc_line(pr.enhance(RAW, [CURRENT], reported)))
        self.assertNotIn("X-THUMBNAIL-URL", attrs)
        self.assertNotIn("X-ARTIST-ID", attrs)
        self.assertEqual(attrs["X-SONG-ID"], '"42"')

    def test_ids_must_be_positive_integers(self):
        for bad in (0, -3, True, "42", 4.2, None):
            reported = dict(REPORTED, song_id=bad, song_artist_id=bad)
            attrs = attributes(rc_line(pr.enhance(RAW, [CURRENT], reported)))
            self.assertNotIn("X-SONG-ID", attrs, bad)
            self.assertNotIn("X-ARTIST-ID", attrs, bad)

    def test_long_values_are_capped_and_bad_urls_dropped(self):
        for url in ("javascript:alert(1)", "https://x/" + "a" * 2000,
                    'https://x/"quoted"', "https://x/a\nb"):
            reported = dict(REPORTED, title="x" * 1000,
                            song_thumbnail_url=url)
            line = rc_line(pr.enhance(RAW, [CURRENT], reported))
            self.assertIn(f'X-TITLE="{"x" * pr.HINT_TEXT_LIMIT}"', line)
            self.assertNotIn("X-THUMBNAIL-URL", line)

    def test_hint_upgrade_keeps_epoch_and_started_at(self):
        # The same boundary is published first without hints (the report
        # is still in flight) and then with them: only X-* attributes are
        # added, STARTED-AT and EPOCH stay byte-identical.
        before = rc_line(pr.enhance(RAW, [CURRENT], None))
        after = rc_line(pr.enhance(RAW, [CURRENT], REPORTED))
        self.assertTrue(after.startswith(before + ",X-TITLE="))


if __name__ == "__main__":
    unittest.main()
