from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.conf import settings
import unfold.decorators

from superapp.apps.admin_portal.admin import SuperAppModelAdmin, SuperAppTabularInline, SuperAppStackedInline
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Stations, StationToStationGroup, StationStreams, StationsMetadataFetch


class StationToStationGroupInline(SuperAppTabularInline):
    model = StationToStationGroup
    fk_name = 'station'
    extra = 0
    autocomplete_fields = ['group']
    fields = ['group', 'order']


class StationStreamsInline(SuperAppTabularInline):
    model = StationStreams
    fk_name = 'station'
    extra = 0
    fields = ['stream_url', 'type', 'order']


class StationsMetadataFetchInline(SuperAppStackedInline):
    model = StationsMetadataFetch
    fk_name = 'station'
    extra = 0
    autocomplete_fields = ['station_metadata_fetch_category']
    readonly_fields = ['url_link']
    fields = ['station_metadata_fetch_category', 'url', 'url_link', 'priority', 'dirty_metadata', 'split_character', 'station_name_regex', 'artist_regex', 'title_regex']

    def url_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', obj.url, obj.url[:50] + '...' if len(obj.url) > 50 else obj.url)
        return _("No URL")
    url_link.short_description = _("URL Link")


@admin.register(Stations, site=superapp_admin_site)
class StationsAdmin(SuperAppModelAdmin):
    list_display = ['title', 'status_indicator', 'thumbnail_preview', 'order', 'website_link', 'groups_display', 'latest_uptime_status']
    list_filter = ['disabled', 'generate_hls_stream', 'feature_latest_post', 'groups', 'created_at']
    search_fields = ['title', 'slug', 'website', 'email']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['latest_station_uptime', 'latest_station_now_playing']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview', 'now_playing_display']

    fieldsets = (
        (_("Basic Information"), {
            'fields': ('title', 'slug', 'order', 'disabled', 'website', 'email')
        }),
        (_("Streaming"), {
            'fields': ('stream_url', 'generate_hls_stream')
        }),
        (_("Media"), {
            'fields': ('thumbnail', 'thumbnail_preview', 'thumbnail_url')
        }),
        (_("Content"), {
            'fields': ('description', 'description_action_title', 'description_link')
        }),
        (_("RSS & Social"), {
            'fields': ('rss_feed', 'feature_latest_post', 'facebook_page_id')
        }),
        (_("Status"), {
            'fields': ('latest_station_uptime', 'latest_station_now_playing', 'now_playing_display')
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    inlines = [StationToStationGroupInline, StationStreamsInline, StationsMetadataFetchInline]

    def status_indicator(self, obj):
        if obj.disabled:
            return format_html('<span style="color: red;">●</span> {}'.format(_("Disabled")))
        return format_html('<span style="color: green;">●</span> {}'.format(_("Active")))
    status_indicator.short_description = _("Status")
    status_indicator.admin_order_field = 'disabled'

    def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail_url
            )
        return _("No image")
    thumbnail_preview.short_description = _("Preview")

    def website_link(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.website, obj.website[:30] + "..." if len(obj.website) > 30 else obj.website)
        return _("No website")
    website_link.short_description = _("Website")

    def groups_display(self, obj):
        groups = obj.groups.all()[:3]  # Limit to first 3 groups
        if groups:
            group_links = []
            for group in groups:
                url = reverse('admin:radio_crestin_stationgroups_change', args=[group.pk])
                group_links.append(format_html('<a href="{}">{}</a>', url, group.name))
            result = ', '.join(group_links)
            if obj.groups.count() > 3:
                result += f' +{obj.groups.count() - 3} more'
            return mark_safe(result)
        return _("No groups")
    groups_display.short_description = _("Groups")

    def latest_uptime_status(self, obj):
        if obj.latest_station_uptime:
            uptime = obj.latest_station_uptime
            status = _("Up") if uptime.is_up else _("Down")
            color = "green" if uptime.is_up else "red"
            return format_html(
                '<span style="color: {};">{}</span> ({}ms)',
                color, status, uptime.latency_ms
            )
        return _("No data")
    latest_uptime_status.short_description = _("Latest Status")

    def now_playing_display(self, obj):
        if obj.latest_station_now_playing:
            try:
                now_playing = obj.latest_station_now_playing
                if now_playing.song:
                    song_info = f"{now_playing.song.name}"
                    if hasattr(now_playing.song, 'artist') and now_playing.song.artist:
                        song_info += f" - {now_playing.song.artist.name}"
                    return format_html(
                        '<div class="p-2.5 bg-gray-100 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600">'
                        '<strong class="text-gray-900 dark:text-white">{}</strong><br>'
                        '<small class="text-gray-600 dark:text-gray-400">Listeners: {}</small><br>'
                        '<small class="text-gray-600 dark:text-gray-400">Updated: {}</small>'
                        '</div>',
                        song_info,
                        now_playing.listeners or 0,
                        now_playing.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    )
                else:
                    return format_html(
                        '<div class="p-2.5 bg-yellow-100 dark:bg-yellow-900 rounded border border-yellow-200 dark:border-yellow-700">'
                        '<span class="text-yellow-800 dark:text-yellow-200">⚠️ No song information available</span><br>'
                        '<small class="text-yellow-700 dark:text-yellow-300">Updated: {}</small>'
                        '</div>',
                        now_playing.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    )
            except Exception as e:
                return format_html(
                    '<div class="p-2.5 bg-red-100 dark:bg-red-900 rounded border border-red-200 dark:border-red-700">'
                    '<span class="text-red-800 dark:text-red-200">❌ Error loading now playing info</span>'
                    '</div>'
                )
        return _("No now playing data")
    now_playing_display.short_description = _("Now Playing Info")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'latest_station_uptime',
            'latest_station_now_playing',
            'latest_station_now_playing__song',
            'latest_station_now_playing__song__artist'
        ).prefetch_related('groups')

    # Admin actions for manual scraping
    actions = ['scrape_metadata_rss_sync', 'scrape_metadata_rss_async']

    # Detail actions for individual stations
    actions_detail = [
        'scrape_single_station_sync',
        'scrape_single_station_async'
    ]

    def _execute_sync_station_tasks_return_results(self, request, station_id):
        """Execute RSS scraping, metadata scraping, and uptime checking synchronously for a single station"""
        successes = []
        errors = []
        
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
                _scrape_rss_sync,
                _scrape_station_sync,
                _check_single_station_uptime
            )
            from superapp.apps.radio_crestin_scraping.services.station_service import StationService
            from superapp.apps.radio_crestin.models import Stations
            
            # Get the station object
            try:
                station = Stations.objects.get(id=station_id, disabled=False)
            except Stations.DoesNotExist:
                errors.append(f"Station {station_id} not found or is disabled")
                return successes, errors
            
            # 1. Check station uptime first
            try:
                uptime_result = _check_single_station_uptime(station)
                if uptime_result.get('success'):
                    status = "UP" if uptime_result.get('is_up') else "DOWN"
                    latency = uptime_result.get('latency_ms', 0)
                    successes.append(f"Uptime check for '{station.title}': {status} ({latency}ms)")
                else:
                    errors.append(f"Uptime check failed for '{station.title}': {uptime_result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"Uptime check error for '{station.title}': {str(e)}")
            
            # 2. RSS scraping
            if station.rss_feed:
                try:
                    rss_result = _scrape_rss_sync(station)
                    
                    if rss_result.get('success'):
                        successes.append(f"RSS feed scraped for '{station.title}': {rss_result.get('posts_count', 0)} posts")
                    else:
                        errors.append(f"RSS scraping failed for '{station.title}': {rss_result.get('error', 'Unknown error')}")
                except Exception as e:
                    errors.append(f"RSS scraping error for '{station.title}': {str(e)}")
            
            # 3. Metadata scraping
            metadata_fetchers = station.station_metadata_fetches.select_related(
                'station_metadata_fetch_category'
            ).order_by('-priority')
            
            if metadata_fetchers.exists():
                try:
                    metadata_result = _scrape_station_sync(station, metadata_fetchers)
                    
                    if metadata_result.get('success'):
                        successes.append(f"Metadata scraped for '{station.title}': {metadata_result.get('scraped_count', 0)} sources")
                    
                    # Add specific errors from metadata scraping
                    if metadata_result.get('errors'):
                        for error in metadata_result['errors']:
                            errors.append(f"Metadata error for '{station.title}': {error}")
                except Exception as e:
                    errors.append(f"Metadata scraping error for '{station.title}': {str(e)}")
                
        except ImportError:
            errors.append("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
        except Exception as e:
            errors.append(f"Unexpected error for station {station_id}: {str(e)}")
        
        return successes, errors

    def scrape_metadata_rss_sync(self, request, queryset):
        """Scrape metadata, RSS feeds, and check uptime for selected stations (synchronous)"""
        total_stations = queryset.count()
        processed_stations = 0
        all_successes = []
        all_errors = []

        for station in queryset:
            processed_stations += 1
            station_successes, station_errors = self._execute_sync_station_tasks_return_results(request, station.id)
            all_successes.extend(station_successes)
            all_errors.extend(station_errors)

        # Show summary results
        if all_successes:
            messages.success(request, f"Processed {processed_stations}/{total_stations} stations successfully. Completed tasks: {len(all_successes)}")

        if all_errors:
            messages.error(request, f"Errors occurred during processing: {len(all_errors)} errors across {processed_stations} stations")

        return HttpResponseRedirect(request.get_full_path())
    scrape_metadata_rss_sync.short_description = _("📡 Scrape metadata, RSS feeds & check uptime (sync)")

    def scrape_metadata_rss_async(self, request, queryset):
        """Scrape metadata, RSS feeds, and check uptime for selected stations (asynchronous)"""
        total_stations = queryset.count()
        station_ids = list(queryset.values_list('id', flat=True))

        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
                scrape_station_metadata,
                scrape_station_rss_feed,
                check_station_uptime
            )

            # Queue all types of tasks
            metadata_tasks = []
            rss_tasks = []
            uptime_tasks = []

            for station_id in station_ids:
                # Queue uptime check first
                uptime_tasks.append(check_station_uptime.delay(station_id))
                # Queue metadata scraping
                metadata_tasks.append(scrape_station_metadata.delay(station_id))
                # Queue RSS scraping
                rss_tasks.append(scrape_station_rss_feed.delay(station_id))

            total_tasks = len(uptime_tasks) + len(metadata_tasks) + len(rss_tasks)
            messages.success(
                request,
                f"Successfully queued {total_tasks} tasks for {total_stations} stations: "
                f"{len(uptime_tasks)} uptime checks, {len(metadata_tasks)} metadata tasks, "
                f"and {len(rss_tasks)} RSS tasks. All tasks are running in the background."
            )

        except ImportError:
            messages.error(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
            )
        except Exception as e:
            if settings.DEBUG:
                raise
            messages.error(request, f"Error queuing async tasks: {str(e)}")

        return HttpResponseRedirect(request.get_full_path())
    scrape_metadata_rss_async.short_description = _("⚡ Scrape metadata, RSS feeds & check uptime (async)")

    def scrape_single_station_sync(self, request, obj):
        """Scrape metadata, RSS feeds, and check uptime for single station (synchronous)"""
        station_successes, station_errors = self._execute_sync_station_tasks_return_results(request, obj.id)

        # Show results
        if station_successes:
            messages.success(
                request, 
                f"Successfully completed {len(station_successes)} tasks for '{obj.title}': " + 
                "; ".join(station_successes)
            )

        if station_errors:
            messages.error(
                request, 
                f"Errors occurred for '{obj.title}': " + "; ".join(station_errors)
            )

        return HttpResponseRedirect(request.get_full_path())
    scrape_single_station_sync.short_description = _("📡 Scrape metadata, RSS & check uptime (sync)")
    scrape_single_station_sync.attrs = {"class": "btn btn-success"}

    def scrape_single_station_async(self, request, obj):
        """Scrape metadata, RSS feeds, and check uptime for single station (asynchronous)"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
                scrape_station_metadata,
                scrape_station_rss_feed,
                check_station_uptime
            )

            # Queue all types of tasks for this single station
            uptime_task = check_station_uptime.delay(obj.id)
            metadata_task = scrape_station_metadata.delay(obj.id)
            rss_task = scrape_station_rss_feed.delay(obj.id)

            messages.success(
                request,
                f"Successfully queued 3 background tasks for '{obj.title}': "
                f"uptime check, metadata scraping, and RSS scraping. "
                f"Tasks are running in the background."
            )

        except ImportError:
            messages.error(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
            )
        except Exception as e:
            if settings.DEBUG:
                raise
            messages.error(request, f"Error queuing async tasks for '{obj.title}': {str(e)}")

        return HttpResponseRedirect(request.get_full_path())
    scrape_single_station_async.short_description = _("⚡ Scrape metadata, RSS & check uptime (async)")
    scrape_single_station_async.attrs = {"class": "btn btn-primary"}
