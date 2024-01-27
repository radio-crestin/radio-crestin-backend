from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Songs, StationGroups, StationMetadataFetchCategories, StationToStationGroup, Stations, \
    StationsMetadataFetch, StationsNowPlaying, StationsUptime, Artists, Posts, StationStreams


@admin.register(Posts)
class PostsAdmin(ImportExportModelAdmin):
    search_fields = ['title', 'link', 'description',]
    list_filter = ('station', 'published', )
    list_display = ('title', 'station')
    readonly_fields = ('created_at', 'updated_at',)


class PostsInline(admin.TabularInline):
    model = Posts
    extra = 0
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at', ]


class StationGroupsInline(admin.TabularInline):
    model = Stations.groups.through
    extra = 0
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at', ]


class StationsMetadataFetchInline(admin.TabularInline):
    model = StationsMetadataFetch
    extra = 0
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at', ]


class StationStreamsInline(admin.TabularInline):
    model = StationStreams
    extra = 0
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at', ]


@admin.register(Stations)
class StationsAdmin(ImportExportModelAdmin):
    search_fields = ['title', 'website', 'email', 'stream_url']
    list_filter = ('latest_station_uptime__is_up', 'groups', )
    list_display = ('title',  'latest_station_now_playing',)
    readonly_fields = ('created_at', 'updated_at', 'thumbnail_url', 'latest_station_uptime', 'latest_station_now_playing',)
    inlines = [
        StationStreamsInline,
        StationGroupsInline,
        StationsMetadataFetchInline,
        PostsInline,
    ]


class StationToStationGroupInline(admin.TabularInline):
    model = StationToStationGroup
    extra = 0
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at', ]


@admin.register(StationGroups)
class StationGroupsAdmin(ImportExportModelAdmin):
    search_fields = ['name', ]
    list_display = ('name',)
    readonly_fields = ('created_at', 'updated_at',)
    inlines = [StationToStationGroupInline]


class StationsMetadataFetchInline(admin.TabularInline):
    model = StationsMetadataFetch
    extra = 0
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at', ]


@admin.register(StationMetadataFetchCategories)
class StationMetadataFetchCategoriesAdmin(ImportExportModelAdmin):
    search_fields = ['slug', ]
    list_display = ('slug',)
    readonly_fields = ('created_at', 'updated_at',)
    inlines = [StationsMetadataFetchInline]


@admin.register(StationToStationGroup)
class StationToStationGroupAdmin(ImportExportModelAdmin):
    search_fields = ['station', 'group']
    list_filter = ('station', 'group')
    list_display = ('station', 'group')
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(StationsMetadataFetch)
class StationsMetadataFetchAdmin(ImportExportModelAdmin):
    search_fields = ['station', 'station_metadata_fetch_category']
    list_filter = ('station', 'station_metadata_fetch_category',)
    list_display = ('station', 'station_metadata_fetch_category',)
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(StationsNowPlaying)
class StationsNowPlayingAdmin(ImportExportModelAdmin):
    search_fields = ['station__title', 'song__name', 'raw_data', 'error']
    list_filter = ('timestamp', 'station', 'song',)
    list_display = ('timestamp', 'station', 'song', 'listeners',)
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(StationsUptime)
class StationsUptimeAdmin(ImportExportModelAdmin):
    search_fields = ['station', 'song', 'raw_data', 'error']
    list_filter = ('timestamp', 'station', 'is_up',)
    list_display = ('timestamp', 'station', 'is_up',)
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(Artists)
class ArtistsAdmin(ImportExportModelAdmin):
    search_fields = ['name', ]
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(Songs)
class SongsAdmin(ImportExportModelAdmin):
    search_fields = ['name', 'artist__name']
    list_filter = ('artist',)
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(StationStreams)
class StationStreamsAdmin(ImportExportModelAdmin):
    search_fields = ['station', 'stream_url']
    list_filter = ('station',)
    readonly_fields = ('created_at', 'updated_at',)
