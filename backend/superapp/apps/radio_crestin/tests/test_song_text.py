from django.test import SimpleTestCase

from ..services.song_text import clean_song_text


class CleanSongTextTests(SimpleTestCase):
    def test_ffmpeg_log_lines_are_rejected(self):
        for line in (
            '[aac @ 0x55d5c8a3e2c0] channel element 3.1 is not allocated',
            '[mp3float @ 000001d2c3e4f5a0] Header missing',
            'ChannelElement 3.1 missing',
        ):
            with self.subTest(line=line):
                self.assertIsNone(clean_song_text(line))

    def test_titles_with_brackets_and_at_signs_survive(self):
        for title in ('[Live @ 2024] Isus', '[Live @ Sala Palatului] Har',
                      'Cântare @ Biserica Betel'):
            with self.subTest(title=title):
                self.assertEqual(clean_song_text(title), title)
