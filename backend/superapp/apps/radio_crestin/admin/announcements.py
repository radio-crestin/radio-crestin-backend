import unfold.decorators
from django.contrib import admin, messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin, SuperAppTabularInline
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..forms.announcement_admin import AnnouncementAdminForm
from ..models import Announcement, AnnouncementImage, AnnouncementSettings, PushSchedule
from ..services import announcement_push, announcement_stats

HTTP_ACTIONS = "action_type == 'external' || action_type == 'in_app_browser'"
SECONDARY_ACTION = "secondary_kind == 'action'"
SECONDARY_HTTP_ACTIONS = (
    f"{SECONDARY_ACTION} && (secondary_action_type == 'external' || secondary_action_type == 'in_app_browser')"
)


def _percent(rate):
    return '-' if rate is None else f'{rate * 100:.1f}%'


def _number(value):
    return f'{value or 0:,}'


class AnnouncementImageInline(SuperAppTabularInline):
    model = AnnouncementImage
    extra = 0
    fields = ['image', 'caption', 'markdown_to_paste']
    readonly_fields = ['markdown_to_paste']
    verbose_name_plural = _('Page images (upload, save, then paste the markdown into the page content)')

    @admin.display(description=_('Markdown to paste'))
    def markdown_to_paste(self, obj):
        return format_html('<code style="user-select:all">{}</code>', obj.markdown) if obj and obj.pk else '-'


@admin.register(Announcement, site=superapp_admin_site)
class AnnouncementAdmin(SuperAppModelAdmin):
    form = AnnouncementAdminForm
    inlines = [AnnouncementImageInline]
    list_display = [
        'title', 'slug', 'category', 'placement', 'status', 'priority', 'starts_at', 'ends_at',
        'impressions', 'unique_viewers_display', 'unique_clickers_display', 'click_rate_display',
        'dismissals', 'push_sent_count',
    ]
    list_filter = ['status', 'placement', 'category', 'push_enabled']
    search_fields = ['title', 'slug']
    autocomplete_fields = ['category', 'station', 'secondary_station', 'stations', 'test_devices']
    readonly_fields = [
        'stats_display', 'events_display', 'push_status_display', 'preview_links_display',
        'push_confirmed_at', 'push_sent_at', 'push_sent_count',
        'impressions', 'clicks', 'secondary_clicks', 'dismissals', 'page_views', 'push_opens',
        'created_at', 'updated_at',
    ]
    actions_detail = ['send_push_notification', 'send_test_notification']
    MAX_TEST_DEVICES = 50
    conditional_fields = {
        'stations': "placement == 'station'",
        'action_label': "action_type != 'none'",
        'action_url': HTTP_ACTIONS,
        'web_link_target': HTTP_ACTIONS,
        'android_intent_uri': "action_type == 'android_intent'",
        'fallback_url': "action_type == 'android_intent'",
        'station': "action_type == 'station'",
        'button_style': "action_type != 'none'",
        'button_color': "action_type != 'none'",
        'button_text_color': "action_type != 'none'",
        'button_icon': "action_type != 'none'",
        'secondary_label': "secondary_kind != 'none'",
        'secondary_later_days': "secondary_kind == 'later'",
        'secondary_action_type': SECONDARY_ACTION,
        'secondary_action_url': SECONDARY_HTTP_ACTIONS,
        'secondary_web_link_target': SECONDARY_HTTP_ACTIONS,
        'secondary_android_intent_uri': f"{SECONDARY_ACTION} && secondary_action_type == 'android_intent'",
        'secondary_fallback_url': f"{SECONDARY_ACTION} && secondary_action_type == 'android_intent'",
        'secondary_station': f"{SECONDARY_ACTION} && secondary_action_type == 'station'",
        'push_schedule': 'push_enabled == true',
        'push_title': 'push_enabled == true',
        'push_body': 'push_enabled == true',
        'push_image': 'push_enabled == true',
    }

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (_('Content'), {'classes': ['tab'], 'fields': [
                'slug', 'category', ('status', 'priority'), 'preview_links_display', 'icon_name', 'icon_image', 'title', 'body_markdown',
            ]}),
            (_('Where it shows'), {'classes': ['tab'], 'fields': ['placement', 'stations']}),
            (_('Button & page'), {'classes': ['tab'], 'fields': [
                'action_type', 'action_label', 'action_url', 'web_link_target',
                'android_intent_uri', 'fallback_url', 'station',
                ('button_style', 'button_icon'), ('button_color', 'button_text_color'),
                'secondary_kind', 'secondary_label', 'secondary_later_days', 'secondary_action_type',
                'secondary_action_url', 'secondary_web_link_target',
                'secondary_android_intent_uri', 'secondary_fallback_url', 'secondary_station',
                'page_title', 'page_cover_image', 'page_markdown',
            ]}),
            (_('Schedule & display'), {'classes': ['tab'], 'fields': [
                ('starts_at', 'ends_at'), 'dismissible', 'hide_after_seconds', 'max_impressions',
            ]}),
            (_('Who sees it'), {'classes': ['tab'], 'description': _(
                "Everything active is in the public list; filters only decide where it is shown, they don't "
                "keep it secret. Use the Preview status for unpublished content."), 'fields': [
                'platforms', 'countries_include', 'countries_exclude', 'locales',
                ('min_app_version', 'max_app_version'),
            ]}),
            (_('Notification'), {'classes': ['tab'], 'fields': [
                'push_enabled', 'push_schedule', 'push_title', 'push_body', 'push_image', 'push_status_display',
                'test_devices',
            ]}),
        ]
        if obj is None:
            return fieldsets
        return [
            (None, {'fields': ['stats_display']}),
            *fieldsets,
            (_('Events'), {'classes': ['tab'], 'fields': [
                'events_display',
                ('impressions', 'clicks', 'secondary_clicks'), ('dismissals', 'page_views', 'push_opens'),
                ('created_at', 'updated_at'),
            ]}),
        ]

    def get_queryset(self, request):
        return announcement_stats.with_unique_counts(super().get_queryset(request).select_related('category'))

    # ------------------------------------------------------------ list columns

    @admin.display(description=_('Unique viewers'), ordering='unique_viewers')
    def unique_viewers_display(self, obj):
        return _number(obj.unique_viewers)

    @admin.display(description=_('Unique clickers'), ordering='unique_clickers')
    def unique_clickers_display(self, obj):
        return _number(obj.unique_clickers)

    @admin.display(description=_('Click rate'))
    def click_rate_display(self, obj):
        return _percent(announcement_stats.click_rate(obj.unique_clickers, obj.unique_viewers))

    # ------------------------------------------------------------ change page blocks

    @admin.display(description=_('Results'))
    def stats_display(self, obj):
        if not obj or not obj.pk:
            return '-'
        stats = announcement_stats.summary(obj)
        status = _('Active') if obj.is_live() else _('Not showing')
        tiles = [
            (_number(obj.impressions), _('Impressions')),
            (_number(stats['unique_viewers']), _('Unique devices')),
            (_number(stats['unique_clickers']), _('Unique clickers')),
            (_percent(stats['click_rate']), _('Click rate (unique)')),
            (_number(stats['unique_closers']), _('Closed (unique)')),
            (_number(obj.push_sent_count), _('Notification sent to')),
        ]
        return format_html(
            '<div style="font-weight:600;margin-bottom:8px">{} · {}</div>'
            '<div style="display:flex;flex-wrap:wrap;gap:20px">{}</div>'
            '<div style="opacity:.65;font-size:12px;margin-top:8px">{}</div>',
            status, timezone.localtime(obj.starts_at).strftime('%d %b %Y %H:%M'),
            format_html_join('', '<div><div style="font-size:20px;font-weight:700">{}</div>'
                                 '<div style="font-size:12px;opacity:.7">{}</div></div>', tiles),
            _('Unique numbers come from the last 180 days of events, counted once per device.'),
        )

    @admin.display(description=_('Breakdown'))
    def events_display(self, obj):
        if not obj or not obj.pk:
            return '-'
        stats = announcement_stats.summary(obj)
        rows = format_html_join(
            '', '<tr><td style="padding:2px 12px 2px 0">{}</td><td style="padding:2px 12px 2px 0">{}</td>'
                '<td style="text-align:right">{}</td></tr>',
            ((row['type'], row['platform'] or '-', _number(row['events'])) for row in stats['by_type_and_platform']),
        )
        targets = stats['clicks_by_target']
        return format_html(
            '<table><thead><tr><th style="text-align:left">{}</th><th style="text-align:left">{}</th>'
            '<th style="text-align:right">{}</th></tr></thead><tbody>{}</tbody></table>'
            '<p style="margin-top:8px">{}: {} {} · {} {} · {} {}</p>',
            _('Event'), _('Platform'), _('Events'), rows or format_html('<tr><td colspan="3">-</td></tr>'),
            _('Clicks by where they tapped'), _('card'), _number(targets.get('card')),
            _('button'), _number(targets.get('button')), _('unknown'), _number(targets.get('')),
        )

    @admin.display(description=_('Status'))
    def push_status_display(self, obj):
        if not announcement_push.is_configured():
            return format_html('<strong style="color:#C2410C">{}</strong>', _(
                'Push is not configured: set FIREBASE_SERVICE_ACCOUNT_JSON to send notifications.'))
        if not obj or not obj.pk:
            return _('Save the announcement to see its reach.')
        reach = announcement_push.reach(obj)
        lines = [_('Reach: Android %(android)s · iPhone %(ios)s · without token %(without)s') % {
            'android': _number(reach['android']), 'ios': _number(reach['ios']),
            'without': _number(reach['without_token']),
        }]
        if obj.push_sent_at:
            lines.append(_('Sent %(when)s to %(count)s phones.') % {
                'when': timezone.localtime(obj.push_sent_at).strftime('%d %b %Y %H:%M'),
                'count': _number(obj.push_sent_count),
            })
        elif obj.push_confirmed_at and obj.push_schedule == PushSchedule.AT_START:
            lines.append(_('Confirmed; it will be sent at the start time.'))
        lines.append(_('Use "Send push notification" at the top of the page to send it.'))
        return format_html_join('', '<div>{}</div>', ((line,) for line in lines))

    @admin.display(description=_('Preview links'))
    def preview_links_display(self, obj):
        settings = AnnouncementSettings.load()
        return format_html(
            '<div>{}</div><div><a href="{}" target="_blank" rel="noopener">{}</a></div>'
            '<div><code style="user-select:all">{}</code></div>',
            _('With the Preview status, it shows only through these links (the token is in Announcement Settings):'),
            settings.website_preview_url, settings.website_preview_url, settings.app_preview_url,
        )

    # ------------------------------------------------------------ push actions

    @unfold.decorators.action(description=_('Send a test notification to these devices'), permissions=['change'])
    def send_test_notification(self, request, object_id):
        announcement = get_object_or_404(Announcement.objects.select_related('category'), pk=object_id)
        if not announcement_push.is_configured():
            messages.error(request, _('Push is not configured: set FIREBASE_SERVICE_ACCOUNT_JSON to send notifications.'))
            return redirect(self._change_url(object_id))
        if request.method not in ('GET', 'POST'):
            return HttpResponseNotAllowed(['GET', 'POST'])
        devices = list(announcement.test_devices.all())
        if not devices:
            messages.warning(request, _('Pick the test devices in the Notification tab and save first.'))
        elif len(devices) > self.MAX_TEST_DEVICES:
            messages.error(request, _('At most %(max)s test devices.') % {'max': self.MAX_TEST_DEVICES})
        elif request.method == 'GET':
            return TemplateResponse(request, 'admin/radio_crestin/confirm_action.html', {
                **self.admin_site.each_context(request),
                'opts': self.model._meta,
                'title': _('Send a test notification to these devices'),
                'lines': [announcement_push.notification_title(announcement),
                          announcement_push.notification_body(announcement)],
                'items': [str(device) for device in devices],
                'confirm_label': _('Send test notification'),
                'cancel_url': self._change_url(object_id),
            })
        else:
            device_count = len(devices)
            result = announcement_push.send_test(announcement)
            without_token = device_count - result['sent'] - result['failed']
            messages.success(request, _(
                'Test notification sent to %(sent)s device(s); %(failed)s failed; %(without)s without a push token.'
            ) % {'sent': result['sent'], 'failed': result['failed'], 'without': max(without_token, 0)})
        return redirect(self._change_url(object_id))

    def _change_url(self, object_id):
        return reverse('admin:radio_crestin_announcement_change', args=(object_id,))

    @unfold.decorators.action(description=_('Send push notification'), permissions=['change'])
    def send_push_notification(self, request, object_id):
        announcement = get_object_or_404(Announcement.objects.select_related('category'), pk=object_id)
        if not announcement_push.is_configured():
            messages.error(request, _('Push is not configured: set FIREBASE_SERVICE_ACCOUNT_JSON to send notifications.'))
            return redirect(self._change_url(object_id))
        if request.method not in ('GET', 'POST'):
            return HttpResponseNotAllowed(['GET', 'POST'])
        if request.method == 'POST' and request.POST.get('confirm') == 'yes':
            return self._confirm_push(request, announcement)
        return self._push_confirmation_page(request, announcement)

    def _waits_for_start(self, announcement):
        return announcement.push_schedule == PushSchedule.AT_START and announcement.starts_at > timezone.now()

    def _push_confirmation_page(self, request, announcement):
        reach = announcement_push.reach(announcement)
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': _('Send push notification'),
            'announcement': announcement,
            'reach': reach,
            'push_title': announcement_push.notification_title(announcement),
            'push_body': announcement_push.notification_body(announcement),
            'waits_for_start': self._waits_for_start(announcement),
            'not_live': not announcement.is_live() and not self._waits_for_start(announcement),
            'change_url': self._change_url(announcement.pk),
        }
        return TemplateResponse(request, 'admin/radio_crestin/announcement/send_push_confirmation.html', context)

    def _confirm_push(self, request, announcement):
        from ..tasks.send_announcement_push import send_announcement_push

        now = timezone.now()
        Announcement.objects.filter(pk=announcement.pk).update(push_enabled=True, push_confirmed_at=now)
        if self._waits_for_start(announcement):
            Announcement.objects.filter(pk=announcement.pk).update(push_sent_at=None)
            messages.success(request, _('Confirmed. The notification will be sent at the start time.'))
        else:
            send_announcement_push.delay(announcement.pk)
            messages.success(request, _('The notification is being sent. The count appears here when it is done.'))
        return redirect(self._change_url(announcement.pk))
