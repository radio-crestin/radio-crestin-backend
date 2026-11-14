"""Rebuilds the website when a station field it renders at build time changes.

Only the fields in WEBSITE_FIELDS count, and only when their value really changed.
Scrapers, uptime checks and now-playing updates write other fields (often through
queryset.update(), which sends no signals), so they never trigger a build.
Announcements are handled in signals/announcements.py.
"""
from django.db.models.fields.files import FieldFile
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

from ..models import StationGroups, StationStreams, Stations, StationToStationGroup
from ..services import web_deploy

# What the website renders, per model (field names).
WEBSITE_FIELDS = {
    Stations: (
        'title', 'slug', 'description', 'description_action_title', 'description_link',
        'thumbnail', 'thumbnail_url', 'stream_url', 'transcode_enabled', 'station_type',
        'order', 'station_order', 'disabled', 'is_public',
        'website', 'email', 'facebook_page_id', 'rss_feed', 'feature_latest_post',
    ),
    StationStreams: ('station', 'stream_url', 'type', 'enabled', 'order', 'station_stream_order'),
    StationGroups: ('slug', 'name', 'station_group_order', 'order'),
    StationToStationGroup: ('station', 'group', 'order', 'station_to_station_group_order'),
}


def _attnames(model):
    return [model._meta.get_field(name).attname for name in WEBSITE_FIELDS[model]]


def _comparable(value):
    return value.name if isinstance(value, FieldFile) else value


def _values(instance) -> dict:
    return {attname: _comparable(getattr(instance, attname)) for attname in _attnames(type(instance))}


def remember_website_values(sender, instance, update_fields=None, **kwargs):
    """The stored values, when this save may touch a website field (None otherwise)."""
    instance._website_values = None
    if instance._state.adding or not instance.pk:
        return
    if update_fields is not None and not set(update_fields) & set(WEBSITE_FIELDS[sender]):
        return
    stored = sender.objects.filter(pk=instance.pk).values(*_attnames(sender)).first()
    instance._website_values = stored and {key: _comparable(value) for key, value in stored.items()}


def rebuild_on_change(sender, instance, created=False, **kwargs):
    if created:
        web_deploy.schedule()
        return
    stored = getattr(instance, '_website_values', None)
    if stored is not None and stored != _values(instance):
        web_deploy.schedule()


def rebuild_on_delete(sender, **kwargs):
    web_deploy.schedule()


def rebuild_on_group_membership_change(sender, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        web_deploy.schedule()


for _model in WEBSITE_FIELDS:
    pre_save.connect(remember_website_values, sender=_model, dispatch_uid=f'website-values-{_model.__name__}')
    post_save.connect(rebuild_on_change, sender=_model, dispatch_uid=f'website-change-{_model.__name__}')
    post_delete.connect(rebuild_on_delete, sender=_model, dispatch_uid=f'website-delete-{_model.__name__}')
m2m_changed.connect(rebuild_on_group_membership_change, sender=Stations.groups.through,
                    dispatch_uid='website-station-groups')
