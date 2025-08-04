import random
import string
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def generate_share_id(length=6):
    """Generate a random share ID."""
    chars = string.ascii_letters + string.digits
    while True:
        share_id = ''.join(random.choices(chars, k=length))
        if not ShareLink.objects.filter(share_id=share_id).exists():
            return share_id


class ShareLink(models.Model):
    """Model for tracking unique share links created by users."""
    
    share_id = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text=_("Unique identifier for the share link")
    )
    
    user = models.OneToOneField(
        'radio_crestin.AppUsers',
        on_delete=models.CASCADE,
        related_name='share_link',
        help_text=_("User who owns this unique share link")
    )
    
    visit_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of unique visits to this share link")
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the share link was created")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Last time the share link was updated")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether the share link is active")
    )
    
    class Meta:
        db_table = 'share_links'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['share_id', 'is_active']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"ShareLink({self.share_id}) by User({self.user_id})"
    
    def get_full_url(self, station_slug=None, domain='asculta.radiocrestin.ro'):
        """Generate the full share URL with optional station."""
        base_url = f"https://{domain}"
        if station_slug:
            return f"{base_url}/{station_slug}?s={self.share_id}"
        return f"{base_url}/?s={self.share_id}"
    
    def increment_visit_count(self):
        """Atomically increment the visit count."""
        self.visit_count = models.F('visit_count') + 1
        self.save(update_fields=['visit_count', 'updated_at'])


class ShareLinkVisit(models.Model):
    """Model for tracking individual visits to share links."""
    
    share_link = models.ForeignKey(
        ShareLink,
        on_delete=models.CASCADE,
        related_name='visits',
        help_text=_("The share link that was visited")
    )
    
    visitor_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address of the visitor")
    )
    
    visitor_user_agent = models.TextField(
        null=True,
        blank=True,
        help_text=_("User agent string of the visitor")
    )
    
    visitor_referer = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text=_("Referer URL if available")
    )
    
    visited_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the visit occurred")
    )
    
    visitor_session_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Session ID to track unique visitors")
    )
    
    class Meta:
        db_table = 'share_link_visits'
        ordering = ['-visited_at']
        indexes = [
            models.Index(fields=['share_link', '-visited_at']),
            models.Index(fields=['visitor_session_id', 'share_link']),
        ]
    
    def __str__(self):
        return f"Visit to {self.share_link.share_id} at {self.visited_at}"