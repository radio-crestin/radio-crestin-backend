from django.db import models
from django.utils.translation import gettext_lazy as _

from ...storage.config import get_public_storage


class PlaylistItemType(models.TextChoices):
    AUDIO = 'audio', _('Audio')
    VIDEO = 'video', _('Video')
    YOUTUBE = 'youtube', _('YouTube')
    # An entire YouTube playlist as one item; `url` holds a full playlist URL
    # (https://www.youtube.com/playlist?list=<ID>). Clients play it via the
    # official IFrame player's playlist mode.
    YOUTUBE_PLAYLIST = 'youtube_playlist', _('YouTube Playlist')


class StationPlaylistItems(models.Model):
    """An ordered media item in a station's managed playlist.

    Used by ``playlist``/``tv`` stations to serve a curated list of
    audio/video/YouTube items instead of (or alongside) a live stream.
    Mirrors the ordering conventions of ``StationStreams``.
    """

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey(
        'Stations',
        verbose_name=_("Station"),
        on_delete=models.CASCADE,
        related_name='playlist_items',
    )
    type = models.CharField(
        _("Type"),
        max_length=16,
        choices=PlaylistItemType.choices,
        default=PlaylistItemType.AUDIO,
    )
    url = models.TextField(
        _("Media URL"),
        help_text=_("Media URL — direct MP3/AAC/MP4 file, HLS .m3u8, or a full YouTube link"),
    )
    title = models.TextField(_("Title"), blank=True, null=False, default="")
    # Optional uploaded artwork; mirrors the Stations.thumbnail conventions.
    # APIs serve a resolved thumbnail (upload wins over `thumbnail_url`), so
    # the wire field stays `thumbnail_url` — see `resolved_thumbnail_url`.
    thumbnail = models.ImageField(
        _("Thumbnail"),
        storage=get_public_storage,
        upload_to='playlist_items/',
        blank=True,
        null=True,
    )
    thumbnail_url = models.URLField(_("Thumbnail URL"), blank=True, null=True)
    duration_seconds = models.IntegerField(_("Duration (seconds)"), blank=True, null=True)
    order = models.IntegerField(_("Order"), default=0)  # Deprecated, use playlist_item_order
    playlist_item_order = models.FloatField(_("Playlist Item Order"), default=0)
    enabled = models.BooleanField(_("Enabled"), default=True)

    class Meta:
        managed = True
        verbose_name = _("Station Playlist Item")
        verbose_name_plural = _("Station Playlist Items")
        db_table = 'station_playlist_items'
        ordering = ('station', 'playlist_item_order',)

    def __str__(self):
        label = self.title or self.url
        return f"{self.station} -> {label}"

    @property
    def resolved_thumbnail_url(self):
        """Thumbnail served to clients: uploaded image wins over the URL."""
        if self.thumbnail:
            return self.thumbnail.url
        return self.thumbnail_url or None

    def save(self, *args, **kwargs):
        self.order = round(self.playlist_item_order) if self.playlist_item_order is not None else 0
        super().save(*args, **kwargs)
