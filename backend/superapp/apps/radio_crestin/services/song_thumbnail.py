"""Rejects song thumbnails that are a station's logo, not the song's cover.

A song is one row per name and artist, shared by every station that plays
it, so the thumbnail stored on it is shown on all of them. Some metadata
APIs send their station's logo for a song they have no cover for: stored on
the song, Aripi Spre Cer's logo was shown for Radio Armonia's songs on
2026-10-13. Without a thumbnail, clients show the playing station's logo.

A logo sent under one fixed URL is rejected by its URL. One sent under a
URL per song ("VA INST" covers) is recognised by its file: each URL is
downloaded once (tasks/check_song_thumbnail.py) and compared with the files
in assets/placeholder_thumbnails/.
"""

import functools
import hashlib
from typing import Optional
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction

from ..models import SongThumbnailChecks

PLACEHOLDER_IMAGES_DIR = settings.BASE_DIR / 'assets' / 'placeholder_thumbnails'
_IMAGE_SUFFIXES = frozenset({'.gif', '.jpeg', '.jpg', '.png', '.webp'})


def is_placeholder_song_thumbnail(url: Optional[str]) -> bool:
    """True for a URL that names a station logo instead of a song cover."""
    if not url:
        return False
    parts = urlsplit(url.strip())
    host = (parts.hostname or '').casefold()
    path = parts.path.casefold()
    file_name = path.rsplit('/', 1)[-1]
    # Aripi Spre Cer's logo, under every category (general/, instrumental/).
    if host.endswith('aripisprecer.ro') and file_name == 'na.png':
        return True
    # radio.co sends the station's logo as the artwork of a bare track.
    if host == 'images.radio.co' and path.startswith('/station_logos/'):
        return True
    # Radio Filadelfia's logo, which its API also sends as a bare file name.
    return file_name.startswith('no_cover_image.')


def clean_song_thumbnail_url(url: Optional[str]) -> Optional[str]:
    """`url` stripped, or None when it is empty or a station logo."""
    if url is None or is_placeholder_song_thumbnail(url):
        return None
    return url.strip() or None


@functools.cache
def _placeholder_image_hashes() -> frozenset[str]:
    return frozenset(
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in PLACEHOLDER_IMAGES_DIR.iterdir()
        if path.suffix.casefold() in _IMAGE_SUFFIXES
    )


def is_placeholder_image(content: bytes) -> bool:
    """True when `content` is byte-identical to a placeholder image."""
    return hashlib.sha256(content).hexdigest() in _placeholder_image_hashes()


def screen_song_thumbnail_url(url: Optional[str]) -> Optional[str]:
    """`url` cleaned, or None when its URL or a past check of its file
    shows it is a station logo."""
    url = clean_song_thumbnail_url(url)
    if url and SongThumbnailChecks.objects.filter(
            url=url, is_placeholder=True).exists():
        return None
    return url


def check_song_thumbnail_later(url: Optional[str]) -> None:
    """Checks the file of a thumbnail URL not checked yet, once the current
    transaction commits, so the report that stored it is not delayed."""
    # Imported here: the task imports is_placeholder_image from this module.
    from ..tasks.check_song_thumbnail import check_song_thumbnail

    if url and not SongThumbnailChecks.objects.filter(url=url).exists():
        transaction.on_commit(lambda: check_song_thumbnail.delay(url))
