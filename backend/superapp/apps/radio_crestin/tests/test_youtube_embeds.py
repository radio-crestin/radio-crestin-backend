import json
from datetime import timedelta

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from ..models import Announcement, AnnouncementEvent
from ..services import youtube_embeds
from ..services.announcement_html import page_html
from ..services.youtube_embeds import Embed

VIDEO = 'dQw4w9WgXcQ'
LIST = 'PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG'
LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


class ParseTests(SimpleTestCase):
    def test_video_url_forms(self):
        for url in (
            f'https://www.youtube.com/watch?v={VIDEO}',
            f'https://youtube.com/watch?v={VIDEO}&feature=share',
            f'https://m.youtube.com/watch?v={VIDEO}',
            f'https://music.youtube.com/watch?v={VIDEO}',
            f'https://youtu.be/{VIDEO}',
            f'http://youtu.be/{VIDEO}?si=abc',
            f'https://www.youtube.com/live/{VIDEO}',
            f'https://www.youtube.com/embed/{VIDEO}',
            f'https://www.youtube-nocookie.com/embed/{VIDEO}',
        ):
            self.assertEqual(youtube_embeds.parse(url), Embed('video', video_id=VIDEO), url)

    def test_shorts(self):
        embed = youtube_embeds.parse(f'https://www.youtube.com/shorts/{VIDEO}')
        self.assertEqual(embed, Embed('short', video_id=VIDEO))
        self.assertEqual(embed.url, f'https://www.youtube.com/shorts/{VIDEO}')

    def test_start_times(self):
        for url, seconds in (
            (f'https://youtu.be/{VIDEO}?t=90', 90),
            (f'https://youtu.be/{VIDEO}?t=90s', 90),
            (f'https://www.youtube.com/watch?v={VIDEO}&t=1h2m3s', 3723),
            (f'https://www.youtube.com/embed/{VIDEO}?start=42', 42),
            (f'https://youtu.be/{VIDEO}?t=soon', None),
        ):
            self.assertEqual(youtube_embeds.parse(url).start, seconds, url)
        self.assertEqual(youtube_embeds.parse(f'https://youtu.be/{VIDEO}?t=90').url,
                         f'https://www.youtube.com/watch?v={VIDEO}&t=90s')

    def test_playlists(self):
        playlist = youtube_embeds.parse(f'https://www.youtube.com/playlist?list={LIST}')
        self.assertEqual(playlist, Embed('playlist', list_id=LIST))
        self.assertEqual(playlist.url, f'https://www.youtube.com/playlist?list={LIST}')
        self.assertEqual(youtube_embeds.parse(f'https://music.youtube.com/playlist?list={LIST}'), playlist)
        self.assertEqual(youtube_embeds.parse(f'https://www.youtube.com/embed/videoseries?list={LIST}'), playlist)

        in_playlist = youtube_embeds.parse(f'https://www.youtube.com/watch?v={VIDEO}&list={LIST}&index=3')
        self.assertEqual(in_playlist, Embed('video', video_id=VIDEO, list_id=LIST))
        self.assertEqual(in_playlist.url, f'https://www.youtube.com/watch?v={VIDEO}&list={LIST}')

    def test_everything_else_stays_a_link(self):
        for url in (
            'https://www.youtube.com/watch?v=short',                    # id too short
            f'https://www.youtube.com/watch?v={VIDEO}x',                # id too long
            'https://www.youtube.com/watch?v=dQw4w9WgXc!',              # bad character
            f'https://www.youtube.com/watch?v={VIDEO}&list=bad',        # list too short
            'https://www.youtube.com/playlist?list=bad list id',
            'https://www.youtube.com/playlist',
            'https://www.youtube.com/@RadioCrestin',                    # channel
            'https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv',
            'https://www.youtube.com/results?search_query=colinde',     # search
            f'https://evil.example/watch?v={VIDEO}',
            f'https://youtube.com.evil.example/watch?v={VIDEO}',
            f'javascript://youtube.com/watch?v={VIDEO}',
            f'ftp://youtu.be/{VIDEO}',
            'not a url',
        ):
            self.assertIsNone(youtube_embeds.parse(url), url)


class PageHtmlEmbedTests(SimpleTestCase):
    def test_a_bare_url_paragraph_becomes_a_facade(self):
        html = page_html(f'Intro.\n\nhttps://youtu.be/{VIDEO}?t=90\n\nOutro.')
        self.assertIn(
            f'<figure class="rc-embed" data-provider="youtube" data-kind="video" data-video-id="{VIDEO}" '
            f'data-start="90"><a href="https://www.youtube.com/watch?v={VIDEO}&amp;t=90s" target="_blank" '
            f'rel="noopener noreferrer"><img src="https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg" '
            f'alt="Miniatură video YouTube" loading="lazy"></a></figure>', html)
        self.assertIn('<p>Intro.</p>', html)
        self.assertNotIn('<iframe', html)

    def test_autolinks_and_links_whose_text_is_the_url(self):
        for markdown in (f'<https://www.youtube.com/shorts/{VIDEO}>',
                         f'[https://www.youtube.com/shorts/{VIDEO}](https://www.youtube.com/shorts/{VIDEO})'):
            self.assertIn('data-kind="short"', page_html(markdown), markdown)

    def test_playlist_without_a_video_is_a_link_card(self):
        html = page_html(f'https://www.youtube.com/playlist?list={LIST}')
        self.assertIn(f'data-kind="playlist" data-list-id="{LIST}"', html)
        self.assertIn('>Listă de redare pe YouTube</a>', html)
        self.assertNotIn('<img', html)

    def test_inline_links_and_invalid_ids_stay_links(self):
        inline = page_html(f'Watch [this](https://youtu.be/{VIDEO}) today, or https://youtu.be/{VIDEO} too.')
        self.assertNotIn('rc-embed', inline)
        self.assertIn(f'href="https://youtu.be/{VIDEO}"', inline)
        for markdown in ('https://youtu.be/tooshort', '[Watch](https://www.youtube.com/watch?v=' + VIDEO + ')',
                         'https://www.youtube.com/@RadioCrestin'):
            self.assertNotIn('rc-embed', page_html(markdown), markdown)

    def test_forged_embeds_lose_everything_unsafe(self):
        html = page_html(
            '<figure class="rc-embed evil" data-provider="youtube" data-kind="video" '
            'data-video-id="javascript:alert(1)" data-list-id="x" data-start="9; drop" data-foo="1" '
            'onclick="steal()" style="x"><img src="javascript:alert(1)" onerror="steal()"></figure>\n\n'
            f'<figure class="rc-embed" data-provider="vimeo" data-video-id="{VIDEO}"></figure>\n\n'
            '<a href="javascript:alert(1)">x</a> <img src="https://x/i.png" loading="javascript:x">'
        )
        for unsafe in ('javascript', 'onclick', 'onerror', 'data-foo', 'evil', 'style', 'steal', 'vimeo',
                       'data-start', 'data-list-id', 'class="rc-embed"'):
            self.assertNotIn(unsafe, html, unsafe)

    def test_a_valid_hand_written_embed_is_kept(self):
        html = page_html(f'<figure class="rc-embed" data-provider="youtube" data-kind="video" '
                         f'data-video-id="{VIDEO}"></figure>')
        self.assertIn(f'class="rc-embed" data-provider="youtube" data-kind="video" data-video-id="{VIDEO}"', html)


@override_settings(CACHES=LOCMEM_CACHE)
class VideoPlayEventTests(TestCase):
    def setUp(self):
        cache.clear()
        self.announcement = Announcement.objects.create(
            slug='videos', title='Videos', status='active', starts_at=timezone.now() - timedelta(hours=1))

    def post(self, *events, device_id='phone-1'):
        return self.client.post('/api/v1/announcements/events/', json.dumps({
            'device_id': device_id, 'events': [{'slug': 'videos', 'type': 'video_play', **event} for event in events],
        }), content_type='text/plain').json()

    def test_counted_once_per_minute_with_its_kind(self):
        self.assertEqual(self.post({'provider': 'youtube', 'kind': 'short'}, {'provider': 'youtube', 'kind': 'video'})
                         ['accepted'], 1)
        self.assertEqual(self.post({'provider': 'youtube', 'kind': 'video'}, device_id='phone-2')['accepted'], 1)
        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.video_plays, 2)
        self.assertEqual(sorted(AnnouncementEvent.objects.values_list('detail', flat=True)),
                         ['youtube:short', 'youtube:video'])

    def test_unknown_providers_and_kinds_are_not_stored(self):
        self.post({'provider': 'vimeo', 'kind': 'video'})
        self.post({'provider': 'youtube', 'kind': '<script>'}, device_id='phone-2')
        self.assertEqual(list(AnnouncementEvent.objects.values_list('detail', flat=True)), ['', ''])
