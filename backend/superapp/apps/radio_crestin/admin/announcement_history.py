"""The History tab of an announcement's admin page: daily and hourly charts, totals, and the CSV download.

Everything reads the rolled-up AnnouncementStatBucket rows, never the raw events.
"""
import csv
import json

from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _, gettext_lazy

from ..models import AnnouncementStatBucket, StatGranularity
from ..models.announcement_events import COUNTER_FIELD_BY_EVENT_TYPE
from ..services.announcement_stat_buckets import DAY_TIME_ZONE

SERIES = [
    # (field, label, color, drawn as)
    ('impressions', gettext_lazy('Impressions'), 'var(--color-primary-500)', 'bar'),
    ('clicks', gettext_lazy('Clicks'), '#16a34a', 'line'),
    ('dismissals', gettext_lazy('Closes'), '#f59e0b', 'line'),
]
CSV_FIELDS = [*COUNTER_FIELD_BY_EVENT_TYPE.values(), 'unique_viewers', 'unique_clickers']
CHART_OPTIONS = {
    'animation': False,
    'responsive': True,
    'maintainAspectRatio': False,
    'interaction': {'mode': 'index', 'intersect': False},
    'plugins': {'legend': {'display': True, 'align': 'end',
                           'labels': {'usePointStyle': True, 'boxWidth': 6, 'boxHeight': 6}}},
    'scales': {
        'x': {'grid': {'display': False}, 'ticks': {'maxTicksLimit': 12}},
        'y': {'beginAtZero': True, 'position': 'left', 'grid': {}},
        # Clicks and closes are far fewer than impressions, so they get their own scale.
        'y1': {'beginAtZero': True, 'position': 'right', 'grid': {'drawOnChartArea': False}},
    },
}


def _local(moment):
    return moment.astimezone(DAY_TIME_ZONE)


def _chart(buckets, label_format):
    data = {
        'labels': [_local(bucket.bucket_start).strftime(label_format) for bucket in buckets],
        'datasets': [
            {
                'label': str(label), 'type': kind, 'data': [getattr(bucket, field) for bucket in buckets],
                'backgroundColor': color, 'borderColor': color,
                'yAxisID': 'y' if kind == 'bar' else 'y1', 'order': 1 if kind == 'bar' else 0,
                **({'borderWidth': 2, 'pointRadius': 0} if kind == 'line' else {'maxBarThickness': 14}),
            }
            for field, label, color, kind in SERIES
        ],
    }
    return format_html(
        '<div style="position:relative;height:220px"><canvas class="chart" data-type="bar" data-value="{}" '
        'data-options="{}"></canvas></div>',
        json.dumps(data), json.dumps(CHART_OPTIONS),
    )


def _totals_row(label, buckets):
    impressions = sum(bucket.impressions for bucket in buckets)
    clicks = sum(bucket.clicks for bucket in buckets)
    rate = f'{clicks / impressions * 100:.1f}%' if impressions else '-'
    return (label, f'{impressions:,}', f'{clicks:,}', f'{sum(bucket.dismissals for bucket in buckets):,}', rate)


def render(announcement, history, updated_until):
    """The History block, from announcement_stats.history()."""
    csv_url = reverse('admin:radio_crestin_announcement_history_csv', args=(announcement.pk,))
    cell = 'padding:4px 16px 4px 0'
    totals = format_html_join('', f'<tr><td style="{cell}">{{}}</td><td style="{cell};text-align:right">{{}}</td>'
                                  f'<td style="{cell};text-align:right">{{}}</td><td style="{cell};text-align:right">{{}}</td>'
                                  f'<td style="text-align:right">{{}}</td></tr>', [
        _totals_row(_('Last 48 hours'), history['hours']),
        _totals_row(_('Last 30 days'), history['days']),
    ])
    updated = (_('Updated every 5 minutes; last update %(when)s.') % {
        'when': timezone.localtime(updated_until).strftime('%d %b %Y %H:%M')} if updated_until
        else _('Not computed yet: it runs every 5 minutes.'))
    return format_html(
        '<div style="display:grid;gap:24px">'
        '<div><div style="font-weight:600;margin-bottom:6px">{}</div>{}</div>'
        '<div><div style="font-weight:600;margin-bottom:6px">{}</div>{}</div>'
        '<div style="overflow-x:auto"><table><thead><tr><th></th><th style="text-align:right;padding-right:16px">{}</th>'
        '<th style="text-align:right;padding-right:16px">{}</th><th style="text-align:right;padding-right:16px">{}</th>'
        '<th style="text-align:right">{}</th></tr></thead><tbody>{}</tbody></table></div>'
        '<div style="font-size:12px;opacity:.7">{} {} <a href="{}?granularity=day">{}</a> · '
        '<a href="{}?granularity=hour">{}</a></div>'
        '</div>',
        _('Per day, last 30 days (Bucharest time)'), _chart(history['days'], '%d %b'),
        _('Per hour, last 48 hours'), _chart(history['hours'], '%a %H:00'),
        _('Impressions'), _('Clicks'), _('Closes'), _('CTR (clicks / impressions)'), totals,
        updated, _('Download CSV:'), csv_url, _('per day'), csv_url, _('per hour'),
    )


def csv_response(announcement, granularity: str) -> HttpResponse:
    """Every stored bucket of one granularity for the announcement, oldest first."""
    if granularity not in StatGranularity.values:
        granularity = StatGranularity.DAY
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{announcement.slug}-{granularity}.csv"'
    writer = csv.writer(response)
    writer.writerow(['start_bucharest', 'start_utc', *CSV_FIELDS])
    rows = (AnnouncementStatBucket.objects.filter(announcement=announcement, granularity=granularity)
            .order_by('bucket_start').values_list('bucket_start', *CSV_FIELDS))
    for start, *counts in rows:
        writer.writerow([_local(start).isoformat(), start.isoformat(), *counts])
    return response
