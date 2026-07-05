"""Dev-only seed data: private test stations for media playback QA.

Creates three private (is_public=False) test stations exercising every
playlist item type (audio / video / youtube / youtube_playlist), an HLS VOD
stream, and a live-style HLS TV station, allowlisted to the given device ids.
Idempotent: re-running updates station fields and replaces playlist items
and streams in place.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from superapp.apps.radio_crestin.models import (
    AppUsers,
    PlaylistItemType,
    StationKind,
    StationPlaylistItems,
    Stations,
    StationStreams,
)

# Stable public media used by the test stations.
YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v=M7lc1UVf-VE'  # YouTube IFrame API demo video
# Playlist referenced by the official YouTube IFrame Player API docs (cuePlaylist example)
YOUTUBE_PLAYLIST_URL = 'https://www.youtube.com/playlist?list=PLC77007E23FF423C6'
BIG_BUCK_BUNNY_MP4 = 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
BIG_BUCK_BUNNY_POSTER = 'https://storage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg'
ELEPHANTS_DREAM_MP4 = 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4'
ELEPHANTS_DREAM_POSTER = 'https://storage.googleapis.com/gtv-videos-bucket/sample/images/ElephantsDream.jpg'
SOUNDHELIX_MP3 = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
MUX_HLS_VOD = 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'
APPLE_BIPBOP_HLS = 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8'

# station_order values well past real stations so test entries sort last.
# playlist_items are listed OLDEST -> NEWEST (playlist_item_order 1..n);
# clients are served newest-first, so e.g. Media Mix plays
# audio -> video -> youtube_playlist -> youtube from the app's perspective.
SEED_STATIONS = [
    {
        'slug': 'test-media-mix-dev',
        'title': 'Test: Media Mix (Dev)',
        'station_type': StationKind.PLAYLIST,
        'station_order': 9001,
        'stream_url': 'https://www.radiocrestin.ro',
        'playlist_items': [
            {
                'type': PlaylistItemType.YOUTUBE,
                'url': YOUTUBE_VIDEO_URL,
                'title': 'YouTube IFrame Player API Demo',
                'thumbnail_url': 'https://i.ytimg.com/vi/M7lc1UVf-VE/hqdefault.jpg',
                'duration_seconds': None,
            },
            {
                'type': PlaylistItemType.YOUTUBE_PLAYLIST,
                'url': YOUTUBE_PLAYLIST_URL,
                'title': 'YouTube IFrame API Docs Demo Playlist',
                'thumbnail_url': None,
                'duration_seconds': None,
            },
            {
                'type': PlaylistItemType.VIDEO,
                'url': BIG_BUCK_BUNNY_MP4,
                'title': 'Big Buck Bunny (MP4)',
                'thumbnail_url': BIG_BUCK_BUNNY_POSTER,
                'duration_seconds': 596,
            },
            {
                'type': PlaylistItemType.AUDIO,
                'url': SOUNDHELIX_MP3,
                'title': 'SoundHelix Song 1 (MP3)',
                'thumbnail_url': None,
                'duration_seconds': 372,
            },
        ],
        'streams': [],
    },
    {
        'slug': 'test-video-hls-mp4-dev',
        'title': 'Test: Video HLS+MP4 (Dev)',
        'station_type': StationKind.PLAYLIST,
        'station_order': 9002,
        'stream_url': 'https://www.radiocrestin.ro',
        'playlist_items': [
            {
                'type': PlaylistItemType.VIDEO,
                'url': MUX_HLS_VOD,
                'title': 'Big Buck Bunny (HLS VOD, mux test stream)',
                'thumbnail_url': BIG_BUCK_BUNNY_POSTER,
                'duration_seconds': None,
            },
            {
                'type': PlaylistItemType.VIDEO,
                'url': ELEPHANTS_DREAM_MP4,
                'title': 'Elephants Dream (MP4)',
                'thumbnail_url': ELEPHANTS_DREAM_POSTER,
                'duration_seconds': 653,
            },
        ],
        'streams': [],
    },
    {
        'slug': 'test-tv-dev',
        'title': 'Test: TV HLS (Dev)',
        'station_type': StationKind.TV,
        'station_order': 9003,
        'stream_url': APPLE_BIPBOP_HLS,
        'playlist_items': [],
        'streams': [
            {
                'type': 'HLS',
                'stream_url': APPLE_BIPBOP_HLS,
                'station_stream_order': 1,
            },
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seed DEV-ONLY private test stations (playlist/TV media playback QA) "
        "allowlisted to the given device ids. Idempotent: re-running updates "
        "the stations and replaces their playlist items/streams."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            action='append',
            dest='device_ids',
            required=True,
            metavar='ANONYMOUS_ID',
            help='Device id (AppUsers.anonymous_id) to allowlist. Repeat for multiple devices.',
        )

    def handle(self, *args, **options):
        device_ids = [d.strip() for d in options['device_ids'] if d and d.strip()]
        if not device_ids:
            self.stderr.write(self.style.ERROR('No non-empty --device-id values given.'))
            return

        users = [self._upsert_app_user(device_id) for device_id in device_ids]

        for spec in SEED_STATIONS:
            station, created = self._upsert_station(spec)
            station.visible_to_devices.set(users)
            items = self._replace_playlist_items(station, spec['playlist_items'])
            streams = self._replace_streams(station, spec['streams'])
            self.stdout.write(
                f"{'Created' if created else 'Updated'} station "
                f"'{station.title}' (slug={station.slug}, type={station.station_type}): "
                f"{items} playlist item(s), {streams} stream(s)"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(SEED_STATIONS)} private test stations, allowlisted to "
            f"{len(device_ids)} device(s): {', '.join(device_ids)}"
        ))
        self.stdout.write(
            'Fetch them via GET /api/v1/private-stations?device_id=<anonymous_id>'
        )

    def _upsert_app_user(self, device_id):
        """Get or create the AppUsers row for a device id.

        Mirrors DeviceRegistrationView minimally: keyed by anonymous_id, with
        device_first_seen_at stamped exactly once.
        """
        user, created = AppUsers.objects.get_or_create(anonymous_id=device_id)
        if user.device_first_seen_at is None:
            user.device_first_seen_at = timezone.now()
            user.save(update_fields=['device_first_seen_at'])
        self.stdout.write(
            f"{'Created' if created else 'Found'} app user for device id '{device_id}'"
        )
        return user

    def _upsert_station(self, spec):
        """Create or update a seed station by slug (safely re-runnable)."""
        fields = {
            'title': spec['title'],
            'station_type': spec['station_type'],
            'station_order': spec['station_order'],
            'stream_url': spec['stream_url'],
            'is_public': False,
            'disabled': False,
            # Keep uptime probes and transcoding pods away from test stations
            'check_uptime': False,
            'transcode_enabled': False,
            'website': 'https://www.radiocrestin.ro',
            'email': 'contact@radiocrestin.ro',
        }
        station, created = Stations.objects.get_or_create(
            slug=spec['slug'], defaults=fields,
        )
        if not created:
            for name, value in fields.items():
                setattr(station, name, value)
            station.save()
        return station, created

    def _replace_playlist_items(self, station, item_specs):
        """Delete and recreate the station's playlist items in order."""
        station.playlist_items.all().delete()
        for index, item in enumerate(item_specs, start=1):
            StationPlaylistItems.objects.create(
                station=station,
                type=item['type'],
                url=item['url'],
                title=item['title'],
                thumbnail_url=item['thumbnail_url'],
                duration_seconds=item['duration_seconds'],
                playlist_item_order=index,
                enabled=True,
            )
        return len(item_specs)

    def _replace_streams(self, station, stream_specs):
        """Delete and recreate the station's streams in order."""
        station.station_streams.all().delete()
        for stream in stream_specs:
            StationStreams.objects.create(
                station=station,
                type=stream['type'],
                stream_url=stream['stream_url'],
                station_stream_order=stream['station_stream_order'],
                enabled=True,
            )
        return len(stream_specs)
