"""Clear now-playing songs that are ffmpeg messages or placeholders.

PodMetadataService rejects such text now, but a song stored before stays
current until its station reports another title, and some never do: alt-fm's
ICY title is empty, so "ChannelElement 3.1 missing" stayed for weeks. This
command ends each such song. now_playing (/stations) loses the song, and a
history row without a song, dated now, ends it in /stations-metadata, which
answers from history. Earlier history rows are kept, so answers for past
instants (cached as immutable) stay true.

Dry run unless --apply.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from superapp.apps.radio_crestin.models import (
    Stations, StationsNowPlaying, StationsNowPlayingHistory,
)
from superapp.apps.radio_crestin.services.history_timeline import (
    stamp_history_row,
)
from superapp.apps.radio_crestin.services.song_text import (
    is_garbage_song_text,
)

# timestamp_source of the history rows this command writes.
CLEANUP_SOURCE = 'cleanup'


class Command(BaseCommand):
    help = (
        "Clear now-playing songs whose name is an ffmpeg log message or a "
        "placeholder. Lists them only, unless --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help="Clear the listed songs (default: only list them).",
        )

    def handle(self, *args, **options):
        garbage = _garbage_now_playing()
        for now_playing in garbage:
            self.stdout.write(
                f"{now_playing.station.slug}: {now_playing.song.name!r} "
                f"(since {now_playing.timestamp.isoformat()})")
        if not options['apply']:
            self.stdout.write(
                f"Dry run: {len(garbage)} now-playing song(s) would be "
                f"cleared. Re-run with --apply to clear them.")
            return
        for now_playing in garbage:
            _clear_song(now_playing.station_id)
        self.stdout.write(self.style.SUCCESS(
            f"Cleared {len(garbage)} now-playing song(s)."))


def _garbage_now_playing():
    """Now-playing rows whose song name is not a song title."""
    rows = (
        StationsNowPlaying.objects
        .filter(song__isnull=False)
        .select_related('station', 'song')
        .order_by('station__slug')
    )
    return [row for row in rows if is_garbage_song_text(row.song.name)]


@transaction.atomic
def _clear_song(station_id: int) -> None:
    """End the station's current song the way a report without a title
    would: no song from now on, recorded in now_playing and in history."""
    # Same lock as the report paths, so the history row is placed after any
    # report written meanwhile.
    Stations.objects.select_for_update(no_key=True).filter(
        id=station_id).values_list('id', flat=True).first()
    now_playing = StationsNowPlaying.objects.get(station_id=station_id)
    if now_playing.song is None or not is_garbage_song_text(
            now_playing.song.name):
        return  # A report replaced the song since it was listed.

    now = timezone.now()
    stamp = stamp_history_row(station_id, now, now, song_changed=True)
    now_playing.song = None
    now_playing.thumbnail_url = None
    now_playing.timestamp = stamp.song_started_at
    now_playing.save(update_fields=[
        'song', 'thumbnail_url', 'timestamp', 'updated_at'])
    StationsNowPlayingHistory.objects.create(
        station_id=station_id,
        timestamp=stamp.timestamp,
        song_started_at=stamp.song_started_at,
        song=None,
        listeners=now_playing.listeners,
        timestamp_source=CLEANUP_SOURCE,
    )
