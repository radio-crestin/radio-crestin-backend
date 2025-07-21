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

from superapp.apps.admin_portal.admin import SuperAppModelAdmin, SuperAppTabularInline
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


class StationsMetadataFetchInline(SuperAppTabularInline):
    model = StationsMetadataFetch
    fk_name = 'station'
    extra = 0
    autocomplete_fields = ['station_metadata_fetch_category']
    fields = ['station_metadata_fetch_category', 'url', 'order']


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
                        '<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">'
                        '<strong>{}</strong><br>'
                        '<small>Listeners: {}</small><br>'
                        '<small>Updated: {}</small>'
                        '</div>',
                        song_info,
                        now_playing.listeners or 0,
                        now_playing.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    )
                else:
                    return format_html(
                        '<div style="padding: 10px; background: #fff3cd; border-radius: 4px;">'
                        '<span style="color: #856404;">⚠️ No song information available</span><br>'
                        '<small>Updated: {}</small>'
                        '</div>',
                        now_playing.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    )
            except Exception as e:
                return format_html(
                    '<div style="padding: 10px; background: #f8d7da; border-radius: 4px;">'
                    '<span style="color: #721c24;">❌ Error loading now playing info</span>'
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
        "sync_all_tasks"
    ]

    def scrape_metadata_rss_sync(self, request, queryset):
        """Scrape metadata and RSS feeds for selected stations (synchronous)"""
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
    scrape_metadata_rss_sync.short_description = _("📡 Scrape metadata and RSS feeds (sync)")

    def scrape_metadata_rss_async(self, request, queryset):
        """Scrape metadata and RSS feeds for selected stations (asynchronous)"""
        total_stations = queryset.count()
        station_ids = list(queryset.values_list('id', flat=True))

        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
                scrape_station_metadata,
                scrape_station_rss_feed
            )

            # Queue metadata scraping tasks
            metadata_tasks = []
            rss_tasks = []

            for station_id in station_ids:
                metadata_tasks.append(scrape_station_metadata.delay(station_id))
                rss_tasks.append(scrape_station_rss_feed.delay(station_id))

            messages.success(
                request,
                f"Successfully queued {len(metadata_tasks)} metadata tasks and {len(rss_tasks)} RSS tasks "
                f"for {total_stations} stations. Tasks are running in the background."
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
    scrape_metadata_rss_async.short_description = _("⚡ Scrape metadata and RSS feeds (async)")

    def _execute_sync_all_tasks(self, request):
        """Execute all scraping tasks synchronously and return errors"""
        errors = []
        successes = []

        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
                scrape_all_stations_metadata,
                scrape_all_stations_rss_feeds,
                cleanup_old_scraped_data
            )

            # Execute metadata scraping synchronously
            try:
                scrape_all_stations_metadata()
                successes.append("Metadata scraping completed")
            except Exception as e:
                if settings.DEBUG:
                    raise  # Re-raise the exception in debug mode for better debugging
                errors.append(f"Metadata scraping failed: {str(e)}")

            # Execute RSS scraping synchronously
            try:
                scrape_all_stations_rss_feeds()
                successes.append("RSS scraping completed")
            except Exception as e:
                if settings.DEBUG:
                    raise  # Re-raise the exception in debug mode for better debugging
                errors.append(f"RSS scraping failed: {str(e)}")

            # Execute cleanup synchronously
            try:
                cleanup_old_scraped_data(days_to_keep=30)
                successes.append("Data cleanup completed")
            except Exception as e:
                if settings.DEBUG:
                    raise  # Re-raise the exception in debug mode for better debugging
                errors.append(f"Data cleanup failed: {str(e)}")

            # Show results to user
            if successes:
                messages.success(request, f"Sync completed successfully: {', '.join(successes)}")

            if errors:
                messages.error(request, f"Sync errors occurred: {'; '.join(errors)}")

        except ImportError:
            messages.error(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
            )
        except Exception as e:
            if settings.DEBUG:
                raise
            messages.error(request, _(f"Error executing sync tasks: {str(e)}"))

    def _execute_sync_station_tasks_return_results(self, request, station_id: int):
        """Execute all scraping tasks for a specific station and return results"""
        errors = []
        successes = []

        try:
            # Get station info for logging
            station = Stations.objects.get(id=station_id)
            station_name = station.title

            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
                scrape_station_metadata,
                scrape_station_rss_feed
            )

            # Execute metadata scraping for this station synchronously
            try:
                result = scrape_station_metadata.apply(args=[station_id]).get(timeout=180)
                if isinstance(result, dict) and result.get('success', False):
                    successes.append(f"Metadata scraping completed for {station_name}")
                else:
                    for error in result.get('errors', []):
                        errors.append(f"Metadata scraping error for {station_name}: {error}")
                    raise Exception("Metadata scraping failed with errors: " + ", ".join(result.get('errors', [])))
            except Exception as e:
                if settings.DEBUG:
                    raise  # Re-raise the exception in debug mode for better debugging
                errors.append(f"Metadata scraping failed for {station_name}: {str(e)}")

            # Execute RSS scraping for this station synchronously
            try:
                result = scrape_station_rss_feed.apply(args=[station_id]).get(timeout=180)
                if isinstance(result, dict) and result.get('success', False):
                    successes.append(f"RSS scraping completed for {station_name}")
                else:
                    error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else 'Unknown error'
                    raise Exception(error_msg)
            except Exception as e:
                if settings.DEBUG:
                    raise  # Re-raise the exception in debug mode for better debugging
                errors.append(f"RSS scraping failed for {station_name}: {str(e)}")

        except Stations.DoesNotExist:
            errors.append(f"Station with ID {station_id} not found")
        except ImportError:
            errors.append("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
        except Exception as e:
            if settings.DEBUG:
                raise
            errors.append(f"Error executing station sync tasks: {str(e)}")

        return successes, errors

    def _execute_sync_station_tasks(self, request, station_id: int):
        """Execute all scraping tasks for a specific station synchronously"""
        successes, errors = self._execute_sync_station_tasks_return_results(request, station_id)

        # Show results to user
        if successes:
            messages.success(request, f"Station sync completed: {'; '.join(successes)}")

        if errors:
            messages.error(request, f"Station sync errors: {'; '.join(errors)}")

    # Detail action for comprehensive sync
    @unfold.decorators.action(description=_("🔄 Sync All Tasks"))
    def sync_all_tasks(self, request, object_id: int):
        """Trigger all scraping tasks for this specific station"""
        self._execute_sync_station_tasks(request, object_id)
        return redirect(reverse_lazy("admin:radio_crestin_stations_change", args=(object_id,)))
