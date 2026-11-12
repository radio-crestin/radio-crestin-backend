from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ...storage.config import get_public_storage
from .announcement_categories import AnnouncementCategory, hex_color_validator
from .stations import Stations
from .users import AppUsers

ICON_NAMES = (
    'whatsapp', 'calendar', 'car', 'megaphone', 'gift', 'heart',
    'bible', 'info', 'warning', 'play', 'star', 'bell',
)
ICON_CHOICES = [(name, name.capitalize()) for name in ICON_NAMES]
BUTTON_ICON_CHOICES = [('auto', _('Automatic from the action')), ('none', _('No icon'))] + ICON_CHOICES

DEFAULT_ANNOUNCEMENT_COLOR = '#0F6E63'


class ActionType(models.TextChoices):
    NONE = 'none', _('No button')
    EXTERNAL = 'external', _('Link outside the app')
    IN_APP_BROWSER = 'in_app_browser', _('In-app browser')
    ANDROID_INTENT = 'android_intent', _('Android intent')
    PAGE = 'page', _('Announcement page')
    STATION = 'station', _('Station')


class WebLinkTarget(models.TextChoices):
    NEW_TAB = 'new_tab', _('New tab')
    SAME_TAB = 'same_tab', _('Same tab')


class ButtonStyle(models.TextChoices):
    FILLED = 'filled', _('Filled')
    OUTLINE = 'outline', _('Outlined')
    TEXT = 'text', _('Text link')
    HIDDEN = 'hidden', _('Hidden (the whole card is tappable)')


class SecondaryButtonKind(models.TextChoices):
    NONE = 'none', _('None')
    CLOSE = 'close', _('Close (same as the X)')
    LATER = 'later', _('Later (hide for N days)')
    ACTION = 'action', _('Own action')


class TargetPlatform(models.TextChoices):
    WEB_MOBILE = 'web_mobile', _('Website on phones')
    WEB_DESKTOP = 'web_desktop', _('Website on desktop')
    ANDROID = 'android', _('Android app')
    IOS = 'ios', _('iOS app')


class PushSchedule(models.TextChoices):
    MANUAL = 'manual', _('Send with the "Send push notification" button')
    AT_START = 'at_start', _('Send automatically at the start time')


class Announcement(models.Model):
    """A short message shown in the card above the station list (website and apps)."""

    slug = models.SlugField(
        _("Slug"), max_length=120, unique=True,
        help_text=_("Closing is remembered per slug. Change it to show this again to people who closed it."),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    priority = models.IntegerField(_("Priority"), default=0, help_text=_("Higher shows first."))
    category = models.ForeignKey(
        AnnouncementCategory, verbose_name=_("Category"), on_delete=models.SET_NULL,
        null=True, blank=True, related_name='announcements',
    )

    # Content
    icon_name = models.CharField(_("Icon"), max_length=32, choices=ICON_CHOICES, blank=True, default='')
    icon_image = models.ImageField(
        _("Icon image"), storage=get_public_storage, upload_to='announcements/icons/', blank=True, null=True,
        help_text=_("Replaces the icon when set."),
    )
    title = models.CharField(_("Title"), max_length=200)
    body_markdown = models.TextField(
        _("Description"), blank=True, default='',
        help_text=_("Inline markdown only: **bold**, *italic*, [link](https://...)."),
    )

    # Primary button
    action_type = models.CharField(_("Action"), max_length=32, choices=ActionType.choices, default=ActionType.NONE)
    action_label = models.CharField(_("Button text"), max_length=80, blank=True, default='')
    action_url = models.URLField(_("Link"), max_length=2000, blank=True, default='')
    web_link_target = models.CharField(
        _("On the website"), max_length=16, choices=WebLinkTarget.choices, default=WebLinkTarget.NEW_TAB,
    )
    android_intent_uri = models.TextField(
        _("Android intent URI"), blank=True, default='', help_text=_("For example intent://...#Intent;package=...;end"),
    )
    fallback_url = models.URLField(
        _("Fallback link"), max_length=2000, blank=True, default='',
        help_text=_("Opened on the website, on iOS, and when the Android intent fails."),
    )
    station = models.ForeignKey(
        Stations, verbose_name=_("Station"), on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    button_style = models.CharField(_("Style"), max_length=16, choices=ButtonStyle.choices, default=ButtonStyle.FILLED)
    button_color = models.CharField(
        _("Color"), max_length=7, blank=True, default='', validators=[hex_color_validator],
        help_text=_("Empty uses the category color."),
    )
    button_text_color = models.CharField(
        _("Label color"), max_length=7, blank=True, default='', validators=[hex_color_validator],
        help_text=_("Empty picks white or black, whichever contrasts more with the button color."),
    )
    button_icon = models.CharField(_("Button icon"), max_length=32, choices=BUTTON_ICON_CHOICES, default='auto')

    # Secondary button
    secondary_kind = models.CharField(
        _("Second button"), max_length=16, choices=SecondaryButtonKind.choices, default=SecondaryButtonKind.NONE,
    )
    secondary_label = models.CharField(_("Second button text"), max_length=80, blank=True, default='')
    secondary_later_days = models.PositiveSmallIntegerField(
        _("Hide for days"), null=True, blank=True, validators=[MinValueValidator(1)],
        help_text=_("For \"Later\": how many days the announcement stays hidden on that device."),
    )
    secondary_action_type = models.CharField(
        _("Second button action"), max_length=32, choices=ActionType.choices, default=ActionType.NONE,
    )
    secondary_action_url = models.URLField(_("Second button link"), max_length=2000, blank=True, default='')
    secondary_web_link_target = models.CharField(
        _("Second button on the website"), max_length=16, choices=WebLinkTarget.choices, default=WebLinkTarget.NEW_TAB,
    )
    secondary_android_intent_uri = models.TextField(_("Second button Android intent URI"), blank=True, default='')
    secondary_fallback_url = models.URLField(_("Second button fallback link"), max_length=2000, blank=True, default='')
    secondary_station = models.ForeignKey(
        Stations, verbose_name=_("Second button station"), on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )

    # Page
    page_title = models.CharField(_("Page title"), max_length=200, blank=True, default='')
    page_cover_image = models.ImageField(
        _("Page cover image"), storage=get_public_storage, upload_to='announcements/pages/', blank=True, null=True,
    )
    page_markdown = models.TextField(
        _("Page content"), blank=True, default='',
        help_text=_("Full markdown: headings, lists, quotes, images and links. Upload images below and paste their markdown."),
    )

    # Schedule and display
    dismissible = models.BooleanField(_("Can be closed"), default=True)
    starts_at = models.DateTimeField(_("Starts at"), default=timezone.now)
    ends_at = models.DateTimeField(_("Ends at"), null=True, blank=True)
    hide_after_seconds = models.PositiveIntegerField(
        _("Hide after seconds"), null=True, blank=True,
        help_text=_("Remove it from the current view after this many seconds on screen."),
    )
    max_impressions = models.PositiveIntegerField(
        _("Max impressions per device"), null=True, blank=True,
    )

    # Targeting: every rule that is set must match; empty means everyone.
    platforms = models.JSONField(_("Platforms"), default=list, blank=True)
    countries_include = models.JSONField(_("Only in countries"), default=list, blank=True)
    countries_exclude = models.JSONField(_("Except countries"), default=list, blank=True)
    locales = models.JSONField(_("Languages"), default=list, blank=True)
    target_devices = models.ManyToManyField(
        AppUsers, verbose_name=_("Devices"), blank=True, related_name='targeted_announcements',
    )
    extra_device_ids = models.JSONField(_("Other device IDs"), default=list, blank=True)
    ip_ranges = models.JSONField(_("IP addresses"), default=list, blank=True)
    min_app_version = models.CharField(_("Min app version"), max_length=32, blank=True, default='')
    max_app_version = models.CharField(_("Max app version"), max_length=32, blank=True, default='')

    # Push notification
    push_enabled = models.BooleanField(_("Also send as notification"), default=False)
    push_schedule = models.CharField(
        _("When"), max_length=16, choices=PushSchedule.choices, default=PushSchedule.MANUAL,
    )
    push_title = models.CharField(_("Notification title"), max_length=120, blank=True, default='')
    push_body = models.CharField(_("Notification text"), max_length=240, blank=True, default='')
    push_image = models.ImageField(
        _("Notification image"), storage=get_public_storage, upload_to='announcements/push/', blank=True, null=True,
    )
    push_confirmed_at = models.DateTimeField(
        _("Notification confirmed at"), null=True, blank=True,
        help_text=_("Set when the send is confirmed; a send at the start time waits for it."),
    )
    push_sent_at = models.DateTimeField(_("Notification sent at"), null=True, blank=True)
    push_sent_count = models.PositiveIntegerField(_("Notification sent to"), default=0)

    # Totals, updated from the reported events
    impressions = models.PositiveBigIntegerField(_("Impressions"), default=0)
    clicks = models.PositiveBigIntegerField(_("Clicks"), default=0)
    secondary_clicks = models.PositiveBigIntegerField(_("Second button clicks"), default=0)
    dismissals = models.PositiveBigIntegerField(_("Closed"), default=0)
    page_views = models.PositiveBigIntegerField(_("Page views"), default=0)
    push_opens = models.PositiveBigIntegerField(_("Notification opens"), default=0)

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        managed = True
        db_table = 'announcements'
        ordering = ('-priority', '-starts_at')
        verbose_name = _("Announcement")
        verbose_name_plural = _("Announcements")
        indexes = [
            models.Index(fields=['is_active', 'ends_at'], name='announcement_active_idx'),
        ]

    def __str__(self):
        return self.title

    @property
    def color(self) -> str:
        if self.button_color:
            return self.button_color
        if self.category_id:
            return self.category.color
        return DEFAULT_ANNOUNCEMENT_COLOR

    def is_live(self, now=None) -> bool:
        now = now or timezone.now()
        return self.is_active and self.starts_at <= now and (self.ends_at is None or self.ends_at > now)


class AnnouncementImage(models.Model):
    """An image uploaded for an announcement's page; paste its markdown into the page content."""

    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_("Image"), storage=get_public_storage, upload_to='announcements/pages/')
    caption = models.CharField(_("Caption"), max_length=200, blank=True, default='')
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'announcement_images'
        ordering = ('created_at',)
        verbose_name = _("Announcement Image")
        verbose_name_plural = _("Announcement Images")

    def __str__(self):
        return self.caption or self.image.name

    @property
    def markdown(self) -> str:
        return f'![{self.caption}]({self.image.url})' if self.image else ''
