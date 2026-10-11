"""song_titles: StreamTitle parsing and title hygiene."""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import song_titles as st  # noqa: E402


class TestTitleFromFfmpegLine:
    def test_mid_stream_update(self):
        line = "[https @ 0x7f8] Metadata update for StreamTitle: Artist - Song"
        assert st.title_from_ffmpeg_line(line) == "Artist - Song"

    def test_startup_dump(self):
        assert st.title_from_ffmpeg_line("    StreamTitle     : Artist - Song") == "Artist - Song"

    def test_decoder_error_continuing_the_dump_line_is_rejected(self):
        # alt-fm, 2026-09-02: the AAC decoder message landed after an empty
        # StreamTitle and was stored as the song name.
        line = "    StreamTitle     : ChannelElement 3.1 missing "
        assert st.title_from_ffmpeg_line(line) is None

    def test_streamtitle_inside_another_message_is_ignored(self):
        line = "[aac @ 0x1] something StreamTitle : not a title"
        assert st.title_from_ffmpeg_line(line) is None

    def test_empty_update_is_no_title(self):
        assert st.title_from_ffmpeg_line("Metadata update for StreamTitle: ") is None


class TestCleanTitle:
    def test_placeholders(self):
        for raw in ("", "  ", "-", "N/A", "null", None):
            assert st.clean_title(raw) is None

    def test_real_titles_survive(self):
        for raw in ("Missing You", "Unknown Soldier - Hope", "LIVE"):
            assert st.clean_title(raw) == raw

    def test_bracketed_title_is_not_an_ffmpeg_address(self):
        assert st.clean_title("[Live @ 2024] Isus") == "[Live @ 2024] Isus"
        assert st.clean_title("[http @ 0x7f8a1c00] Opening") is None
        assert st.clean_title("[aac @ 000001d2c3a4b5c6] error") is None

    def test_whitespace_is_collapsed(self):
        assert st.clean_title("  Artist  -   Song ") == "Artist - Song"


class TestTitlesMatch:
    def test_same_song_formatted_differently(self):
        assert st.titles_match("Grace Will Lead You Home", "Artist - Grace will lead you home")
        assert st.titles_match("Sa-L slăvim pe Dumnezeu", "sa l slavim pe dumnezeu")

    def test_different_songs(self):
        assert not st.titles_match("Un radio de Cuvant", "Shine Jesus Shine")

    def test_short_titles_need_an_exact_match(self):
        assert not st.titles_match("Joy", "Radio Joy - ID Statie")
        assert not st.titles_match("", "x")
