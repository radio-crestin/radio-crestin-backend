"""YouTube links that become embeds in an announcement's page.

A page paragraph that is only a YouTube URL is turned into a placeholder figure
(a link with the thumbnail, never an iframe); the clients turn it into a player.
Anything that isn't exactly a video, Short or playlist with valid IDs stays a link.
"""
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlsplit

from django.utils.html import format_html, format_html_join

VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
LIST_ID = re.compile(r'^[A-Za-z0-9_-]{10,64}$')
DURATION = re.compile(r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$')
HOSTS = {
    'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
    'youtu.be', 'www.youtu.be', 'youtube-nocookie.com', 'www.youtube-nocookie.com',
}
PATH_VIDEOS = {'shorts': 'short', 'live': 'video', 'embed': 'video'}
KINDS = ('video', 'playlist', 'short')
THUMBNAIL = 'https://i.ytimg.com/vi/{}/hqdefault.jpg'
THUMBNAIL_URL = re.compile(r'^https://i\.ytimg\.com/[A-Za-z0-9_./-]+(\?[A-Za-z0-9_=&.-]*)?$')

# Romanian copy produced with `codex exec`.
ALT_VIDEO = 'Miniatură video YouTube'
ALT_SHORT = 'Miniatură YouTube Shorts'
PLAYLIST_LINK = 'Listă de redare pe YouTube'


@dataclass(frozen=True)
class Embed:
    kind: str  # video | playlist | short
    video_id: Optional[str] = None
    list_id: Optional[str] = None
    start: Optional[int] = None

    @property
    def url(self) -> str:
        """The canonical link: also what the clients open when the player can't play."""
        if self.kind == 'playlist':
            return 'https://www.youtube.com/playlist?' + urlencode({'list': self.list_id})
        if self.kind == 'short':
            return f'https://www.youtube.com/shorts/{self.video_id}'
        query = {'v': self.video_id}
        if self.list_id:
            query['list'] = self.list_id
        if self.start:
            query['t'] = f'{self.start}s'
        return 'https://www.youtube.com/watch?' + urlencode(query)

    @property
    def key(self) -> str:
        """What its details are stored under: the video id, or the list id for a playlist."""
        return self.video_id or self.list_id


def parse_start(value: Optional[str]) -> Optional[int]:
    """'90', '90s' or '1h2m3s' -> seconds; None when absent or not a duration."""
    match = DURATION.match(value or '')
    if not value or not match:
        return None
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    total = hours * 3600 + minutes * 60 + seconds
    return total or None


def parse(url: str) -> Optional[Embed]:
    """The embed a YouTube URL stands for, or None when it should stay a plain link."""
    try:
        parts = urlsplit((url or '').strip())
    except ValueError:
        return None
    if parts.scheme not in ('http', 'https') or (parts.hostname or '') not in HOSTS:
        return None
    query = parse_qs(parts.query)
    segments = [segment for segment in parts.path.split('/') if segment]
    list_id = (query.get('list') or [None])[0]
    start = parse_start((query.get('t') or query.get('start') or [None])[0])

    kind, video_id = 'video', None
    if parts.hostname.endswith('youtu.be'):
        video_id = segments[0] if len(segments) == 1 else None
    elif segments == ['watch']:
        video_id = (query.get('v') or [None])[0]
    elif segments == ['playlist'] or segments == ['embed', 'videoseries']:
        kind = 'playlist'
    elif len(segments) == 2 and segments[0] in PATH_VIDEOS:
        kind, video_id = PATH_VIDEOS[segments[0]], segments[1]
    else:
        return None  # channels, search pages, anything else

    if list_id is not None and not LIST_ID.match(list_id):
        return None
    if kind == 'playlist':
        return Embed('playlist', list_id=list_id) if list_id else None
    if not video_id or not VIDEO_ID.match(video_id):
        return None
    if kind == 'short':
        return Embed('short', video_id=video_id)
    return Embed('video', video_id=video_id, list_id=list_id, start=start)


def thumbnail(embed: Embed, details: dict) -> Optional[str]:
    """The fetched thumbnail (playlists have no fixed one), else the video's standard one."""
    return details.get('thumbnail') or (THUMBNAIL.format(embed.video_id) if embed.video_id else None)


def figure(embed: Embed, details: Optional[dict] = None) -> str:
    """The placeholder the page HTML carries (sanitized again afterwards): a thumbnail and the link."""
    details = details or {}
    title, image = details.get('title'), thumbnail(embed, details)
    attributes = format_html_join(' ', '{}="{}"', [
        (name, value) for name, value in (
            ('class', 'rc-embed'), ('data-provider', 'youtube'), ('data-kind', embed.kind),
            ('data-video-id', embed.video_id), ('data-list-id', embed.list_id), ('data-start', embed.start),
            ('data-title', title), ('data-thumbnail', image),
        ) if value
    ])
    if image:
        fallback = {'short': ALT_SHORT, 'playlist': PLAYLIST_LINK}.get(embed.kind, ALT_VIDEO)
        content = format_html('<a href="{}"><img src="{}" alt="{}" loading="lazy"></a>',
                              embed.url, image, title or fallback)
    else:
        content = format_html('<a href="{}">{}</a>', embed.url, title or PLAYLIST_LINK)
    return format_html('<figure {}>{}</figure>', attributes, content)


def api_item(embed: Embed, details: Optional[dict] = None) -> dict:
    """One entry of page.embeds in the single-announcement API (the app reads the markdown)."""
    details = details or {}
    item = {
        'url': embed.url, 'provider': 'youtube', 'kind': embed.kind,
        'video_id': embed.video_id, 'list_id': embed.list_id, 'start': embed.start,
        'title': details.get('title'), 'thumbnail': thumbnail(embed, details),
    }
    return {key: value for key, value in item.items() if value is not None}


def is_valid_attribute(attribute: str, value: str) -> bool:
    """Values a figure.rc-embed attribute may carry: clients build player URLs from them."""
    checks = {
        'data-provider': lambda v: v == 'youtube',
        'data-kind': lambda v: v in KINDS,
        'data-video-id': lambda v: bool(VIDEO_ID.match(v)),
        'data-list-id': lambda v: bool(LIST_ID.match(v)),
        'data-start': lambda v: v.isdigit() and len(v) <= 6,
        'data-title': lambda v: 0 < len(v) <= MAX_TITLE_LENGTH,
        'data-thumbnail': lambda v: bool(THUMBNAIL_URL.match(v)),
    }
    check = checks.get(attribute)
    return bool(check and check(value))


# ---------------------------------------------------------------- details from YouTube

OEMBED_URL = 'https://www.youtube.com/oembed'
OEMBED_TIMEOUT_SECONDS = 3
MAX_TITLE_LENGTH = 200


def clean_title(value) -> Optional[str]:
    """A title fit for an attribute: text only, one line, at most MAX_TITLE_LENGTH characters."""
    if not isinstance(value, str):
        return None
    text = ' '.join(''.join(char if char.isprintable() else ' ' for char in value).split())
    return text[:MAX_TITLE_LENGTH] or None


def clean_thumbnail(value) -> Optional[str]:
    """Only https thumbnails on i.ytimg.com."""
    return value if isinstance(value, str) and THUMBNAIL_URL.match(value) else None


def fetch_details(embed: Embed) -> dict:
    """{title, thumbnail} from YouTube's public oEmbed (no API key); {} on any failure."""
    import requests

    try:
        response = requests.get(OEMBED_URL, params={'url': embed.url, 'format': 'json'},
                                timeout=OEMBED_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    details = {'title': clean_title(data.get('title')), 'thumbnail': clean_thumbnail(data.get('thumbnail_url'))}
    return {key: value for key, value in details.items() if value}


def details_for(embeds, known: dict) -> dict:
    """{key: details} for these embeds: known ones are kept, missing ones fetched (failures retried next save)."""
    found, tried = {}, set()
    for embed in embeds:
        if embed.key in tried:
            continue  # the same video twice on a page is fetched once
        tried.add(embed.key)
        details = known.get(embed.key) or fetch_details(embed)
        if details:
            found[embed.key] = details
    return found
