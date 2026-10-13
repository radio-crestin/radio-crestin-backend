"""Rejects song thumbnails that are a station's logo, not the song's cover.

A song is one row per name and artist, shared by every station that plays
it, so the thumbnail stored on it is shown on all of them. Some metadata
APIs send their station's logo for a song they have no cover for: stored on
the song, Aripi Spre Cer's logo was shown for Radio Armonia's songs on
2026-10-13. Without a thumbnail, clients show the playing station's logo.
"""

from typing import Optional
from urllib.parse import urlsplit


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
