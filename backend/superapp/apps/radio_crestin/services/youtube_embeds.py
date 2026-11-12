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


def figure(embed: Embed) -> str:
    """The placeholder the page HTML carries (sanitized again afterwards)."""
    attributes = format_html_join(' ', '{}="{}"', [
        (name, value) for name, value in (
            ('class', 'rc-embed'), ('data-provider', 'youtube'), ('data-kind', embed.kind),
            ('data-video-id', embed.video_id), ('data-list-id', embed.list_id), ('data-start', embed.start),
        ) if value
    ])
    if embed.video_id:
        alt = ALT_SHORT if embed.kind == 'short' else ALT_VIDEO
        content = format_html('<a href="{}"><img src="{}" alt="{}" loading="lazy"></a>',
                              embed.url, THUMBNAIL.format(embed.video_id), alt)
    else:
        content = format_html('<a href="{}">{}</a>', embed.url, PLAYLIST_LINK)
    return format_html('<figure {}>{}</figure>', attributes, content)


def is_valid_attribute(attribute: str, value: str) -> bool:
    """Values a figure.rc-embed attribute may carry: clients build player URLs from them."""
    checks = {
        'data-provider': lambda v: v == 'youtube',
        'data-kind': lambda v: v in KINDS,
        'data-video-id': lambda v: bool(VIDEO_ID.match(v)),
        'data-list-id': lambda v: bool(LIST_ID.match(v)),
        'data-start': lambda v: v.isdigit() and len(v) <= 6,
    }
    check = checks.get(attribute)
    return bool(check and check(value))
