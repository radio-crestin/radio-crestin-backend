"""Downloads a song thumbnail once and, when its file is a placeholder
image, removes it from every song (services/song_thumbnail.py)."""

import hashlib
import ipaddress
import logging
import socket
from typing import Optional
from urllib.parse import urlsplit

import requests
from celery import shared_task
from django.db import transaction

from ..models import Songs, SongThumbnailChecks, StationsNowPlaying
from ..services.song_thumbnail import is_placeholder_image

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT_SECONDS = 10
MAX_IMAGE_BYTES = 5 * 1024 * 1024


@shared_task(queue='priority', ignore_result=True)
def check_song_thumbnail(url: str) -> None:
    """Records whether `url` is a placeholder image. A URL that cannot be
    downloaded is not recorded, so it is checked again when a station next
    reports it."""
    if SongThumbnailChecks.objects.filter(url=url).exists():
        return
    content = _download(url)
    if content is None:
        return
    is_placeholder = is_placeholder_image(content)
    with transaction.atomic():
        _, created = SongThumbnailChecks.objects.get_or_create(url=url, defaults={
            'sha256': hashlib.sha256(content).hexdigest(),
            'is_placeholder': is_placeholder,
        })
        if created and is_placeholder:
            songs = Songs.objects.filter(thumbnail_url=url).update(
                thumbnail_url=None)
            StationsNowPlaying.objects.filter(thumbnail_url=url).update(
                thumbnail_url=None)
            logger.info("Cleared placeholder thumbnail %s from %d song(s)",
                        url, songs)


def _download(url: str) -> Optional[bytes]:
    """The file at `url`, or None when it is not a public http(s) URL or
    does not answer 200 with at most MAX_IMAGE_BYTES."""
    if not _is_public_http_url(url):
        return None
    try:
        # No redirects: each hop would need the public-address check again.
        with requests.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS, stream=True,
                          allow_redirects=False) as response:
            if response.status_code != 200:
                return None
            content = response.raw.read(MAX_IMAGE_BYTES + 1,
                                        decode_content=True)
    except (requests.RequestException, OSError) as error:
        logger.info("Could not download thumbnail %s: %s", url, error)
        return None
    return content if 0 < len(content) <= MAX_IMAGE_BYTES else None


def _is_public_http_url(url: str) -> bool:
    """True when `url` is http(s) and its host resolves only to public
    addresses. The URLs come from third-party metadata APIs, and the worker
    must not be made to request internal services."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            return False
        infos = socket.getaddrinfo(parts.hostname, parts.port)
    except (ValueError, UnicodeError, OSError):
        return False
    return all(ipaddress.ip_address(info[4][0]).is_global for info in infos)
