import unfold.decorators
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.enums import ActionVariant

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import ContactKind, ContactMessage, ContactStatus
from ..services import contact_drafts

ANSWER_LABELS = {
    'relation': _('Relation to the station'),
    'station_name': _('Station name'),
    'website': _('Website'),
    'listen_url': _('Where to listen'),
    'description': _('Description'),
    'denomination': _('Denomination'),
    'denomination_other': _('Denomination (other)'),
    'mission': _('Mission'),
    'station_email': _('Station email'),
    'facebook_url': _('Facebook'),
    'consent': _('Station agrees to be listed'),
    'note': _('Note'),
    'about': _('About'),
    'station_slug': _('Station'),
    'title': _('Title'),
    'summary': _('Card text'),
    'details': _('Page text'),
    'link': _('Link'),
    'starts_on': _('Starts on'),
    'ends_on': _('Ends on'),
}
LINK_ANSWERS = {'website', 'listen_url', 'facebook_url', 'link'}


def new_messages_badge(request):
    """Sidebar badge: how many messages nobody opened yet."""
    return ContactMessage.objects.filter(status=ContactStatus.NEW).count() or None


def _answer_html(name, value):
    if name in LINK_ANSWERS:
        # Only http(s) links are accepted by the form, so they are safe to link.
        return format_html('<a href="{0}" target="_blank" rel="noopener noreferrer">{0}</a>', value)
    if isinstance(value, bool):
        return _('Yes') if value else _('No')
    return format_html('<span style="white-space:pre-wrap">{}</span>', value)


@admin.register(ContactMessage, site=superapp_admin_site)
class ContactMessageAdmin(SuperAppModelAdmin):
    list_display = ['subject', 'kind', 'status', 'name', 'email', 'source', 'created_at']
    list_filter = ['kind', 'status', 'source']
    search_fields = ['subject', 'name', 'email', 'message']
    date_hierarchy = 'created_at'
    actions = ['mark_done', 'mark_spam']
    actions_detail = ['create_draft_station', 'create_draft_announcement']
    fieldsets = [
        (None, {'fields': ['status', 'admin_notes', 'drafts_display']}),
        (_('Message'), {'fields': ['kind', 'name', 'email', 'phone', 'message', 'answers_display', 'images_display']}),
        (_('Sent from'), {'fields': [
            'source', 'platform', 'app_version', 'device_id', 'ip', 'country', 'user_agent', 'created_at',
        ]}),
    ]
    readonly_fields = [
        'drafts_display', 'kind', 'name', 'email', 'phone', 'message', 'answers_display', 'images_display',
        'source', 'platform', 'app_version', 'device_id', 'ip', 'country', 'user_agent', 'created_at',
    ]

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_station', 'created_announcement')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Opening a new message moves it to "In progress".
        ContactMessage.objects.filter(pk=object_id, status=ContactStatus.NEW).update(status=ContactStatus.IN_PROGRESS)
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description=_('Answers'))
    def answers_display(self, obj):
        rows = [(ANSWER_LABELS.get(name, name), _answer_html(name, value)) for name, value in obj.details.items()]
        if not rows:
            return '-'
        return format_html(
            '<table>{}</table>',
            format_html_join('', '<tr><th style="padding-right:1rem;text-align:left">{}</th><td>{}</td></tr>', rows),
        )

    @admin.display(description=_('Images'))
    def images_display(self, obj):
        images = list(obj.images.all())
        if not images:
            return '-'
        return format_html_join(
            '', '<a href="{0}" target="_blank" rel="noopener noreferrer" title="{1}">'
                '<img src="{0}" style="max-height:160px;margin:0 .5rem .5rem 0;border-radius:6px"></a>',
            ((image.image.url, image.get_role_display()) for image in images),
        )

    @admin.display(description=_('Created from this message'))
    def drafts_display(self, obj):
        links = []
        if obj.created_station_id:
            links.append((reverse('admin:radio_crestin_stations_change', args=(obj.created_station_id,)),
                          _('Station: %s') % obj.created_station))
        if obj.created_announcement_id:
            links.append((reverse('admin:radio_crestin_announcement_change', args=(obj.created_announcement_id,)),
                          _('Announcement: %s') % obj.created_announcement))
        return format_html_join(' · ', '<a href="{}">{}</a>', links) if links else '-'

    @admin.action(description=_('Mark as done'))
    def mark_done(self, request, queryset):
        queryset.update(status=ContactStatus.DONE)

    @admin.action(description=_('Mark as spam'))
    def mark_spam(self, request, queryset):
        queryset.update(status=ContactStatus.SPAM)

    def _is_kind(self, object_id, kind) -> bool:
        return ContactMessage.objects.filter(pk=object_id, kind=kind).exists()

    def has_create_draft_station_permission(self, request, object_id=None):
        return (request.user.has_perm('radio_crestin.add_stations')
                and (object_id is None or self._is_kind(object_id, ContactKind.STATION)))

    def has_create_draft_announcement_permission(self, request, object_id=None):
        return (request.user.has_perm('radio_crestin.add_announcement')
                and (object_id is None or self._is_kind(object_id, ContactKind.ANNOUNCEMENT)))

    @unfold.decorators.action(
        description=_('Create draft station'), icon='radio', variant=ActionVariant.PRIMARY,
        permissions=['create_draft_station'],
    )
    def create_draft_station(self, request, object_id):
        message = get_object_or_404(ContactMessage, pk=object_id)
        try:
            station = contact_drafts.create_station(message)
        except contact_drafts.DraftError as error:
            messages.error(request, str(error))
            return redirect(reverse('admin:radio_crestin_contactmessage_change', args=(object_id,)))
        messages.success(request, _(
            'Draft station created: disabled and private. Check the stream link, logo and details, then enable it.'
        ))
        return redirect(reverse('admin:radio_crestin_stations_change', args=(station.pk,)))

    @unfold.decorators.action(
        description=_('Create draft announcement'), icon='campaign', variant=ActionVariant.PRIMARY,
        permissions=['create_draft_announcement'],
    )
    def create_draft_announcement(self, request, object_id):
        message = get_object_or_404(ContactMessage, pk=object_id)
        try:
            announcement = contact_drafts.create_announcement(message)
        except contact_drafts.DraftError as error:
            messages.error(request, str(error))
            return redirect(reverse('admin:radio_crestin_contactmessage_change', args=(object_id,)))
        messages.success(request, _('Draft announcement created. Review the text, category and dates, then set it to Active.'))
        return redirect(reverse('admin:radio_crestin_announcement_change', args=(announcement.pk,)))
