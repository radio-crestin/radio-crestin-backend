# Import all admin classes from individual files
from .admin.artists import ArtistsAdmin
from .admin.songs import SongsAdmin
from .admin.station_groups import StationGroupsAdmin
from .admin.station_metadata_fetch_categories import StationMetadataFetchCategoriesAdmin
from .admin.stations import StationsAdmin
from .admin.station_streams import StationStreamsAdmin
from .admin.posts import PostsAdmin
from .admin.stations_now_playing import StationsNowPlayingAdmin
from .admin.stations_uptime import StationsUptimeAdmin

__all__ = [
    'ArtistsAdmin',
    'SongsAdmin',
    'StationGroupsAdmin',
    'StationMetadataFetchCategoriesAdmin',
    'StationsAdmin',
    'StationStreamsAdmin',
    'PostsAdmin',
    'StationsNowPlayingAdmin',
    'StationsUptimeAdmin',
]