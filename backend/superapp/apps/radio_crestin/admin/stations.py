from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
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
    actions = ['scrape_metadata_selected', 'scrape_rss_selected', 'scrape_both_selected']
    
    # Detail actions for individual stations
    actions_detail = [
        "scrape_metadata_single",
        "scrape_rss_single", 
        "scrape_both_single"
    ]

    def scrape_metadata_selected(self, request, queryset):
        """Manually trigger metadata scraping for selected stations"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_metadata
            
            queued_count = 0
            for station in queryset:
                scrape_station_metadata.delay(station.id)
                queued_count += 1
            
            self.message_user(
                request,
                _(f"Successfully queued metadata scraping for {queued_count} station(s). Tasks are running in the background."),
                messages.SUCCESS
            )
        except ImportError:
            self.message_user(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed."),
                messages.ERROR
            )
        except Exception as e:
            self.message_user(
                request,
                _(f"Error queuing scraping tasks: {str(e)}"),
                messages.ERROR
            )
    scrape_metadata_selected.short_description = _("🔄 Scrape metadata for selected stations")

    def scrape_rss_selected(self, request, queryset):
        """Manually trigger RSS scraping for selected stations"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_rss_feed
            
            queued_count = 0
            stations_with_rss = 0
            for station in queryset:
                if station.rss_feed:
                    scrape_station_rss_feed.delay(station.id)
                    queued_count += 1
                stations_with_rss += 1 if station.rss_feed else 0
            
            if stations_with_rss == 0:
                self.message_user(
                    request,
                    _("None of the selected stations have RSS feeds configured."),
                    messages.WARNING
                )
            else:
                self.message_user(
                    request,
                    _(f"Successfully queued RSS scraping for {queued_count} station(s) out of {stations_with_rss} with RSS feeds. Tasks are running in the background."),
                    messages.SUCCESS
                )
        except ImportError:
            self.message_user(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed."),
                messages.ERROR
            )
        except Exception as e:
            self.message_user(
                request,
                _(f"Error queuing RSS scraping tasks: {str(e)}"),
                messages.ERROR
            )
    scrape_rss_selected.short_description = _("📰 Scrape RSS feeds for selected stations")

    def scrape_both_selected(self, request, queryset):
        """Manually trigger both metadata and RSS scraping for selected stations"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_metadata, scrape_station_rss_feed
            
            metadata_queued = 0
            rss_queued = 0
            
            for station in queryset:
                # Queue metadata scraping
                scrape_station_metadata.delay(station.id)
                metadata_queued += 1
                
                # Queue RSS scraping if station has RSS feed
                if station.rss_feed:
                    scrape_station_rss_feed.delay(station.id)
                    rss_queued += 1
            
            message = _(f"Successfully queued scraping for {metadata_queued} station(s): metadata scraping for all, RSS scraping for {rss_queued} stations with RSS feeds. Tasks are running in the background.")
            self.message_user(request, message, messages.SUCCESS)
            
        except ImportError:
            self.message_user(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed."),
                messages.ERROR
            )
        except Exception as e:
            self.message_user(
                request,
                _(f"Error queuing scraping tasks: {str(e)}"),
                messages.ERROR
            )
    scrape_both_selected.short_description = _("🔄📰 Scrape both metadata and RSS for selected stations")

    # Detail actions for individual stations
    @unfold.decorators.action(description=_("🔄 Scrape metadata for this station"))
    def scrape_metadata_single(self, request, object_id: int):
        """Manually trigger metadata scraping for a single station"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_metadata
            
            station = Stations.objects.get(pk=object_id)
            scrape_station_metadata.delay(station.id)
            
            messages.success(
                request,
                _(f"Successfully queued metadata scraping for station '{station.title}'. Task is running in the background.")
            )
        except Stations.DoesNotExist:
            messages.error(request, _("Station not found."))
        except ImportError:
            messages.error(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
            )
        except Exception as e:
            messages.error(request, _(f"Error queuing scraping task: {str(e)}"))
        
        return redirect(reverse_lazy("admin:radio_crestin_stations_change", args=(object_id,)))

    @unfold.decorators.action(description=_("📰 Scrape RSS feed for this station"))
    def scrape_rss_single(self, request, object_id: int):
        """Manually trigger RSS scraping for a single station"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_rss_feed
            
            station = Stations.objects.get(pk=object_id)
            
            if not station.rss_feed:
                messages.warning(
                    request,
                    _(f"Station '{station.title}' does not have an RSS feed configured.")
                )
            else:
                scrape_station_rss_feed.delay(station.id)
                messages.success(
                    request,
                    _(f"Successfully queued RSS scraping for station '{station.title}'. Task is running in the background.")
                )
        except Stations.DoesNotExist:
            messages.error(request, _("Station not found."))
        except ImportError:
            messages.error(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
            )
        except Exception as e:
            messages.error(request, _(f"Error queuing RSS scraping task: {str(e)}"))
        
        return redirect(reverse_lazy("admin:radio_crestin_stations_change", args=(object_id,)))

    @unfold.decorators.action(description=_("🔄📰 Scrape both metadata and RSS for this station"))
    def scrape_both_single(self, request, object_id: int):
        """Manually trigger both metadata and RSS scraping for a single station"""
        try:
            from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_metadata, scrape_station_rss_feed
            
            station = Stations.objects.get(pk=object_id)
            
            # Queue metadata scraping
            scrape_station_metadata.delay(station.id)
            tasks_queued = ["metadata"]
            
            # Queue RSS scraping if station has RSS feed
            if station.rss_feed:
                scrape_station_rss_feed.delay(station.id)
                tasks_queued.append("RSS")
            
            tasks_str = " and ".join(tasks_queued)
            message = _(f"Successfully queued {tasks_str} scraping for station '{station.title}'. Tasks are running in the background.")
            
            if not station.rss_feed and len(tasks_queued) == 1:
                message += _(" Note: RSS scraping was skipped as this station has no RSS feed configured.")
            
            messages.success(request, message)
            
        except Stations.DoesNotExist:
            messages.error(request, _("Station not found."))
        except ImportError:
            messages.error(
                request,
                _("Scraping tasks are not available. Make sure radio_crestin_scraping app is installed.")
            )
        except Exception as e:
            messages.error(request, _(f"Error queuing scraping tasks: {str(e)}"))
        
        return redirect(reverse_lazy("admin:radio_crestin_stations_change", args=(object_id,)))