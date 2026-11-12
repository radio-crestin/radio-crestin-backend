import json
from datetime import timedelta
from unittest.mock import Mock, patch

import requests

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
            f'data-start="90" data-thumbnail="https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg"><a href="https://www.youtube.com/watch?v={VIDEO}&amp;t=90s" target="_blank" '
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


def oembed(**data):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = data
    return response


class FetchDetailsTests(SimpleTestCase):
    def test_title_and_thumbnail(self):
        with patch('requests.get', return_value=oembed(
                title='  Way Maker\n(Live)  ', thumbnail_url=f'https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg')) as get:
            details = youtube_embeds.fetch_details(Embed('video', video_id=VIDEO))
        self.assertEqual(details, {'title': 'Way Maker (Live)',
                                   'thumbnail': f'https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg'})
        self.assertEqual(get.call_args.kwargs['params'],
                         {'url': f'https://www.youtube.com/watch?v={VIDEO}', 'format': 'json'})
        self.assertLessEqual(get.call_args.kwargs['timeout'], 5)

    def test_failures_give_nothing(self):
        for error in (requests.Timeout('slow'), requests.ConnectionError('down'), ValueError('not json')):
            with patch('requests.get', side_effect=error):
                self.assertEqual(youtube_embeds.fetch_details(Embed('video', video_id=VIDEO)), {}, error)

    def test_only_ytimg_thumbnails_and_capped_titles(self):
        for bad in ('http://i.ytimg.com/vi/x/hq.jpg', 'https://evil.example/x.jpg',
                    'https://i.ytimg.com.evil.example/x.jpg', 'javascript:alert(1)', 'https://i.ytimg.com/a"b.jpg'):
            with patch('requests.get', return_value=oembed(title='T', thumbnail_url=bad)):
                self.assertEqual(youtube_embeds.fetch_details(Embed('playlist', list_id=LIST)), {'title': 'T'}, bad)
        with patch('requests.get', return_value=oembed(title='x' * 500)):
            self.assertEqual(len(youtube_embeds.fetch_details(Embed('video', video_id=VIDEO))['title']), 200)

    def test_known_details_are_not_fetched_again(self):
        with patch('requests.get') as get:
            found = youtube_embeds.details_for([Embed('video', video_id=VIDEO)], {VIDEO: {'title': 'Known'}})
        get.assert_not_called()
        self.assertEqual(found, {VIDEO: {'title': 'Known'}})


class PageHtmlDetailsTests(SimpleTestCase):
    def test_title_is_escaped_in_data_title_and_alt(self):
        html = page_html(f'https://youtu.be/{VIDEO}', {VIDEO: {'title': '"Quoted" <script>x</script> & co'}})
        self.assertIn('data-title="&quot;Quoted&quot; &lt;script&gt;x&lt;/script&gt; &amp; co"', html)
        self.assertIn('alt="&quot;Quoted&quot; &lt;script&gt;x&lt;/script&gt; &amp; co"', html)
        self.assertNotIn('<script>', html)

    def test_playlist_thumbnail(self):
        thumb = 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'
        html = page_html(f'https://www.youtube.com/playlist?list={LIST}', {LIST: {'title': 'Lista', 'thumbnail': thumb}})
        self.assertIn(f'data-thumbnail="{thumb}"', html)
        self.assertIn(f'<img src="{thumb}" alt="Lista" loading="lazy">', html)

    def test_forged_thumbnail_and_title_outside_an_embed_are_dropped(self):
        html = page_html(f'<figure class="rc-embed" data-provider="youtube" data-video-id="{VIDEO}" '
                         f'data-thumbnail="https://evil.example/x.jpg"></figure>\n\n'
                         '<figure data-title="loose" data-thumbnail="https://i.ytimg.com/vi/x/hq.jpg"></figure>')
        self.assertNotIn('evil.example', html)
        self.assertNotIn('loose', html)
        self.assertNotIn('data-thumbnail="https://i.ytimg.com/vi/x/hq.jpg"', html)


@override_settings(CACHES=LOCMEM_CACHE)
class StoredDetailsTests(TestCase):
    PAGE = (f'Intro.\n\nhttps://www.youtube.com/shorts/{VIDEO}\n\n'
            f'https://www.youtube.com/playlist?list={LIST}\n\nhttps://youtu.be/{VIDEO}?t=90')

    def setUp(self):
        cache.clear()

    def make(self, **fields):
        return Announcement.objects.create(slug='videos', title='Videos', status='active',
                                           starts_at=timezone.now() - timedelta(hours=1), **fields)

    def test_fetched_on_save_once_per_id_and_served_without_network(self):
        with patch('requests.get', return_value=oembed(
                title='Jireh', thumbnail_url='https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg')) as get:
            announcement = self.make(page_title='Videos', page_markdown=self.PAGE)
            self.assertEqual(get.call_count, 2)  # one per id: the video (twice on the page) and the list
            announcement.title = 'Renamed'
            announcement.save()
            self.assertEqual(get.call_count, 2)
        self.assertEqual(set(announcement.embed_details), {VIDEO, LIST})

        with patch('requests.get') as get:
            page = self.client.get('/api/v1/announcements/videos/').json()['page']
        get.assert_not_called()
        self.assertEqual(page['embeds'], [
            {'url': f'https://www.youtube.com/shorts/{VIDEO}', 'provider': 'youtube', 'kind': 'short',
             'video_id': VIDEO, 'title': 'Jireh', 'thumbnail': 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'},
            {'url': f'https://www.youtube.com/playlist?list={LIST}', 'provider': 'youtube', 'kind': 'playlist',
             'list_id': LIST, 'title': 'Jireh', 'thumbnail': 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'},
            {'url': f'https://www.youtube.com/watch?v={VIDEO}&t=90s', 'provider': 'youtube', 'kind': 'video',
             'video_id': VIDEO, 'start': 90, 'title': 'Jireh',
             'thumbnail': 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'},
        ])
        self.assertIn('data-title="Jireh"', page['html'])
        self.assertNotIn('embeds', self.client.get('/api/v1/announcements/').content.decode())

    def test_a_failed_fetch_is_retried_on_the_next_save(self):
        with patch('requests.get', side_effect=requests.Timeout('slow')):
            announcement = self.make(page_markdown=f'https://youtu.be/{VIDEO}')
        self.assertEqual(announcement.embed_details, {})
        page = self.client.get('/api/v1/announcements/videos/').json()['page']
        self.assertEqual(page['embeds'], [{'url': f'https://www.youtube.com/watch?v={VIDEO}', 'provider': 'youtube',
                                           'kind': 'video', 'video_id': VIDEO,
                                           'thumbnail': f'https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg'}])
        self.assertIn('alt="Miniatură video YouTube"', page['html'])
        with patch('requests.get', return_value=oembed(title='Now known')):
            announcement.save()
        self.assertEqual(announcement.embed_details, {VIDEO: {'title': 'Now known'}})

    def test_removed_embeds_are_forgotten(self):
        with patch('requests.get', return_value=oembed(title='Old')):
            announcement = self.make(page_markdown=f'https://youtu.be/{VIDEO}')
            announcement.page_markdown = 'No videos now.'
            announcement.save()
        self.assertEqual(announcement.embed_details, {})


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
