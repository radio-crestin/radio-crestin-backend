"""Report stations whose live transcoding and HLS streams disagree.

A transcoded station has a streaming pod serving its live playlist under
TRANSCODED_HLS_PREFIX, but the apps only play HLS from an enabled
`station_streams` row of type HLS. Without such a row the pod transcodes for
nobody; with one but no transcoding, the apps try a playlist that does not
exist. Editors curate station_streams, so this command only reports, and it
exits with status 1 when it finds anything (for ops checks and CI).
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Exists, OuterRef

from superapp.apps.radio_crestin.models import Stations, StationStreams

# Where the streaming pods publish a transcoded station's playlists
# (StationType.hls_stream_url).
TRANSCODED_HLS_PREFIX = "https://live.radiocrestin.ro/hls/"


class Command(BaseCommand):
    help = (
        "List stations whose live transcoding and enabled HLS streams "
        "disagree. Exits with status 1 when any are found."
    )

    def handle(self, *args, **options):
        problems = [
            *self._transcoded_without_hls(),
            *self._hls_without_transcoding(),
        ]
        for problem in problems:
            self.stdout.write(problem)
        if problems:
            raise CommandError(
                f"{len(problems)} station(s) need an editor's decision.",
                returncode=1,
            )
        self.stdout.write(self.style.SUCCESS(
            "Transcoding and HLS streams agree for every station."))

    @staticmethod
    def _transcoded_without_hls():
        """Stations the pods transcode (the selection of
        `streaming_station_configs`) that no app plays over HLS."""
        enabled_hls = StationStreams.objects.filter(
            station=OuterRef('pk'), type='HLS', enabled=True)
        stations = Stations.objects.filter(
            disabled=False, transcode_enabled=True,
        ).filter(~Exists(enabled_hls)).order_by('slug')
        return [
            f"Transcoded without an enabled HLS stream: {s.slug} (add "
            f"{TRANSCODED_HLS_PREFIX}{s.slug}/index.m3u8 or turn "
            f"transcoding off)"
            for s in stations
        ]

    @staticmethod
    def _hls_without_transcoding():
        """Enabled HLS streams on the pods' host whose station is not
        transcoded. Other hosts' HLS streams (TV stations) are fine."""
        streams = StationStreams.objects.filter(
            type='HLS',
            enabled=True,
            stream_url__startswith=TRANSCODED_HLS_PREFIX,
            station__disabled=False,
            station__transcode_enabled=False,
        ).select_related('station').order_by('station__slug', 'id')
        return [
            f"HLS stream without transcoding: {s.station.slug} "
            f"({s.stream_url})"
            for s in streams
        ]
