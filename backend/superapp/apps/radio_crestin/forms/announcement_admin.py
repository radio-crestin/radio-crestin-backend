"""The announcement edit form: list fields typed one per line, a markdown preview, and the button rules."""
import re

from django import forms
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget, UnfoldAdminTextareaWidget

from ..models import ActionType, Announcement, ButtonStyle, Placement, TargetPlatform

RESERVED_SLUGS = {'events'}  # /api/v1/announcements/events/ is the events endpoint
LOCALE_PATTERN = re.compile(r'^[a-z]{2,3}([-_][a-z0-9]{2,8})*$', re.IGNORECASE)


class MarkdownPreviewWidget(UnfoldAdminTextareaWidget):
    """A textarea with a live preview next to it (static/radio_crestin/announcements/markdown_preview.js)."""

    def __init__(self, mode='inline', attrs=None):
        self.mode = mode
        super().__init__(attrs={'rows': 6, **(attrs or {}), 'data-markdown-preview': mode})

    def render(self, name, value, attrs=None, renderer=None):
        textarea = super().render(name, value, attrs, renderer)
        return format_html(
            '<div class="announcement-md">{}<div class="announcement-md__preview" data-preview-for="{}" '
            'aria-live="polite"></div></div>',
            textarea, (attrs or {}).get('id', f'id_{name}'),
        )

    class Media:
        css = {'all': ('radio_crestin/announcements/markdown_preview.css',)}
        js = ('radio_crestin/announcements/markdown_preview.js',)


class ListTextField(forms.CharField):
    """A list typed as text: one value per line, commas and spaces also separate."""

    widget = UnfoldAdminTextareaWidget

    def __init__(self, *, normalize=str.strip, validate_item=None, **kwargs):
        self.normalize, self.validate_item = normalize, validate_item
        kwargs.setdefault('required', False)
        super().__init__(**kwargs)
        self.widget.attrs['rows'] = 2

    def prepare_value(self, value):
        return '\n'.join(value) if isinstance(value, (list, tuple)) else value

    def to_python(self, value):
        items = [self.normalize(item) for item in re.split(r'[\s,;]+', super().to_python(value) or '') if item]
        return list(dict.fromkeys(items))

    def validate(self, value):
        super().validate(value)
        invalid = [item for item in value if self.validate_item and not self.validate_item(item)]
        if invalid:
            raise forms.ValidationError(_('Not valid: %(items)s'), params={'items': ', '.join(invalid)})


class AnnouncementAdminForm(forms.ModelForm):
    platforms = forms.MultipleChoiceField(
        label=_('Platforms'), choices=TargetPlatform.choices, required=False,
        widget=UnfoldAdminCheckboxSelectMultipleWidget, help_text=_('None ticked means everywhere.'),
    )
    countries_include = ListTextField(
        label=_('Only in countries'), normalize=str.upper, validate_item=lambda item: re.fullmatch(r'[A-Z]{2}', item),
        help_text=_('ISO codes such as RO, MD, DE. Empty means everyone.'),
    )
    countries_exclude = ListTextField(
        label=_('Except countries'), normalize=str.upper, validate_item=lambda item: re.fullmatch(r'[A-Z]{2}', item),
    )
    locales = ListTextField(
        label=_('Languages'), validate_item=LOCALE_PATTERN.match,
        help_text=_('Language codes such as ro, en or hu; ro also matches ro-RO and ro_RO.'),
    )
    class Meta:
        model = Announcement
        # Written by the server: event totals and the push send state.
        exclude = [
            'impressions', 'clicks', 'secondary_clicks', 'dismissals', 'page_views', 'push_opens', 'video_plays',
            'push_confirmed_at', 'push_sent_at', 'push_sent_count',
        ]
        widgets = {
            'body_markdown': MarkdownPreviewWidget(mode='inline', attrs={'rows': 4}),
            'page_markdown': MarkdownPreviewWidget(mode='full', attrs={'rows': 16}),
        }
        help_texts = {
            'body_markdown': _(
                'Inline markdown only: **bold**, *italic*, [link](https://...). About 3 lines fit on the card; '
                'longer text is cut with an ellipsis. Optional when the card has a button with a label.'
            ),
            'page_markdown': _(
                'Full markdown: headings, lists, quotes, images and links. Upload images below and paste their '
                'markdown. Paste a YouTube link on its own line to embed it.'
            ),
            'push_title': _('Plain text. Empty uses the announcement title.'),
            'push_body': _('Plain text. Empty uses the description without markdown.'),
        }

    def clean_slug(self):
        slug = self.cleaned_data['slug']
        if slug in RESERVED_SLUGS:
            raise forms.ValidationError(_('This slug is reserved.'))
        return slug

    def clean(self):
        data = super().clean()
        self._require_icon(data)
        self._check_schedule(data)
        self._check_placement(data)
        self._check_button(data)
        self._require_body_or_button(data)
        return data

    def _require(self, data, field, message):
        if not data.get(field):
            self.add_error(field, message)

    def _require_body_or_button(self, data):
        """No card is ever empty: without a visible button (an action with a label) it needs a description."""
        has_button = data.get('action_type') not in (None, ActionType.NONE) and (data.get('action_label') or '').strip()
        if not (data.get('body_markdown') or '').strip() and not has_button:
            self.add_error('body_markdown', _('Write a description, or add a button with a label.'))

    def _require_icon(self, data):
        if not data.get('icon_name') and not data.get('icon_image'):
            self.add_error('icon_name', _('Pick an icon or upload an image.'))

    def _check_schedule(self, data):
        starts_at, ends_at = data.get('starts_at'), data.get('ends_at')
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error('ends_at', _('The end must be after the start.'))

    def _check_placement(self, data):
        if data.get('placement') == Placement.STATION and not data.get('stations'):
            self.add_error('stations', _('Pick at least one station.'))

    def _check_action(self, data, action_type):
        if action_type in (ActionType.EXTERNAL, ActionType.IN_APP_BROWSER):
            self._require(data, 'action_url', _('This action needs a link.'))
        elif action_type == ActionType.ANDROID_INTENT:
            self._require(data, 'android_intent_uri', _('This action needs an Android intent URI.'))
            self._require(data, 'fallback_url', _('Websites and iPhones open the fallback link.'))
        elif action_type == ActionType.STATION:
            self._require(data, 'station', _('Pick the station to start.'))
        elif action_type == ActionType.FORM:
            self._require(data, 'form', _('Pick the form to open.'))
        elif action_type == ActionType.PAGE and not (data.get('page_title') or data.get('page_markdown')):
            self.add_error('page_markdown', _('Write the announcement page.'))

    def _check_button(self, data):
        action_type = data.get('action_type')
        if action_type == ActionType.NONE:
            return
        if data.get('button_style') != ButtonStyle.HIDDEN:
            self._require(data, 'action_label', _('Write the button text, or choose the hidden style.'))
        self._check_action(data, action_type)
