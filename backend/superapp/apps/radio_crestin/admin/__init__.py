from .artists import ArtistsAdmin
from .songs import SongsAdmin
from .station_groups import StationGroupsAdmin
from .station_metadata_fetch_categories import StationMetadataFetchCategoriesAdmin
from .stations import StationsAdmin
from .station_streams import StationStreamsAdmin
from .posts import PostsAdmin
from .stations_now_playing import StationsNowPlayingAdmin
from .stations_uptime import StationsUptimeAdmin

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