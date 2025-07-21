# Import all admin classes from individual files
from .admin.artists import ArtistsAdmin
from .admin.songs import SongsAdmin
from .admin.station_groups import StationGroupsAdmin
from .admin.station_metadata_fetch_categories import StationMetadataFetchCategoriesAdmin
from .admin.station_to_station_group import StationToStationGroupAdmin
from .admin.stations import StationsAdmin
from .admin.station_streams import StationStreamsAdmin
from .admin.stations_metadata_fetch import StationsMetadataFetchAdmin
from .admin.posts import PostsAdmin
from .admin.stations_now_playing import StationsNowPlayingAdmin
from .admin.stations_uptime import StationsUptimeAdmin
from .admin.listening_sessions import ListeningSessionsAdmin
from .admin.reviews import ReviewsAdmin
from .admin.app_users import AppUsersAdmin

__all__ = [
    'ArtistsAdmin',
    'SongsAdmin',
    'StationGroupsAdmin',
    'StationMetadataFetchCategoriesAdmin',
    'StationToStationGroupAdmin',
    'StationsAdmin',
    'StationStreamsAdmin',
    'StationsMetadataFetchAdmin',
    'PostsAdmin',
    'StationsNowPlayingAdmin',
    'StationsUptimeAdmin',
    'ListeningSessionsAdmin',
    'ReviewsAdmin',
    'AppUsersAdmin',
]