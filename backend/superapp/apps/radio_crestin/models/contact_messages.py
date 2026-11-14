import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from ...storage.config import get_private_storage
from .announcements import Announcement
from .stations import Stations


class ContactKind(models.TextChoices):
    GENERAL = 'general', _('General message')
    STATION = 'station', _('New station')
    ANNOUNCEMENT = 'announcement', _('Announcement request')
    REPORT = 'report', _('Station report')
    FEEDBACK = 'feedback', _('Suggestion')


class ContactStatus(models.TextChoices):
    NEW = 'new', _('New')
    IN_PROGRESS = 'in_progress', _('In progress')
    DONE = 'done', _('Done')
    SPAM = 'spam', _('Spam')


class ContactMessage(models.Model):
    """A message sent from the website's contact forms; `details` holds the kind's own answers."""

    kind = models.CharField(_("Kind"), max_length=16, choices=ContactKind.choices)
    status = models.CharField(
        _("Status"), max_length=16, choices=ContactStatus.choices, default=ContactStatus.NEW, db_index=True,
    )
    subject = models.CharField(
        _("Subject"), max_length=200, blank=True, default='',
        help_text=_("The station name, the announcement title or the start of the message."),
    )
    name = models.CharField(_("Name"), max_length=100, blank=True, default='')
    email = models.EmailField(_("Email"), max_length=254)
    phone = models.CharField(_("Phone"), max_length=40, blank=True, default='')
    message = models.TextField(_("Message"), blank=True, default='')
    details = models.JSONField(_("Answers"), default=dict, blank=True)

    # Where it came from
    source = models.CharField(_("Source"), max_length=16, blank=True, default='')
    platform = models.CharField(_("Platform"), max_length=32, blank=True, default='')
    app_version = models.CharField(_("App version"), max_length=32, blank=True, default='')
    device_id = models.CharField(_("Device ID"), max_length=128, blank=True, default='')
    ip = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    country = models.CharField(_("Country"), max_length=2, blank=True, default='')
    user_agent = models.CharField(_("User agent"), max_length=300, blank=True, default='')

    # What the admin made of it
    admin_notes = models.TextField(_("Admin notes"), blank=True, default='')
    created_station = models.ForeignKey(
        Stations, verbose_name=_("Created station"), on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    created_announcement = models.ForeignKey(
        Announcement, verbose_name=_("Created announcement"), on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        managed = True
        db_table = 'contact_messages'
        ordering = ('-created_at',)
        verbose_name = _("Contact Message")
        verbose_name_plural = _("Contact Messages")

    def __str__(self):
        return f"{self.get_kind_display()}: {self.subject or self.email}"


def _image_path(_instance, filename):
    return f"contact/{uuid.uuid4().hex}{filename[filename.rfind('.'):]}"


class ContactImageRole(models.TextChoices):
    LOGO = 'logo', _('Station logo')
    IMAGE = 'image', _('Image')


class ContactMessageImage(models.Model):
    """An image sent with a contact message, re-encoded on upload and kept in private storage."""

    message = models.ForeignKey(ContactMessage, on_delete=models.CASCADE, related_name='images')
    role = models.CharField(_("Role"), max_length=16, choices=ContactImageRole.choices, default=ContactImageRole.IMAGE)
    image = models.ImageField(_("Image"), storage=get_private_storage, upload_to=_image_path)
    width = models.PositiveIntegerField(_("Width"), default=0)
    height = models.PositiveIntegerField(_("Height"), default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'contact_message_images'
        ordering = ('message', 'id')
        verbose_name = _("Contact Message Image")
        verbose_name_plural = _("Contact Message Images")

    def __str__(self):
        return self.image.name
