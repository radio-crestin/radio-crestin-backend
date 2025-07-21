from django.db import models
from django.utils.translation import gettext_lazy as _


class AppUsers(models.Model):
    anonymous_id = models.CharField(_("Anonymous ID"), max_length=512, unique=True, help_text=_("Unique identifier for the user, used for analytics and tracking."))
    
    # Reference to the current anonymous session ID from NGINX
    current_anonymous_session_id = models.CharField(
        _("Current Anonymous Session ID"), 
        max_length=512, 
        blank=True, 
        null=True,
        help_text=_("Most recent anonymous session identifier from NGINX logs")
    )
    
    # Track last activity for session management
    last_activity = models.DateTimeField(
        _("Last Activity"), 
        blank=True, 
        null=True,
        help_text=_("Last recorded activity timestamp")
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)

    class Meta:
        managed = True  # This is now a managed table that syncs with authentication_user
        db_table = 'app_users'
        verbose_name = _("App User")
        verbose_name_plural = _("App Users")
        indexes = [
            models.Index(fields=['current_anonymous_session_id']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"App User {self.anonymous_id}"
    
    @classmethod
    def get_or_create_by_session_id(cls, anonymous_session_id):
        """
        Get or create a user based on anonymous session ID.
        
        Args:
            anonymous_session_id: Session ID from NGINX
            
        Returns:
            Tuple of (user, created) where created is True for new users
        """
        from django.utils import timezone
        
        # Try to find existing user with this session ID
        try:
            user = cls.objects.get(current_anonymous_session_id=anonymous_session_id)
            # Update last activity
            user.last_activity = timezone.now()
            user.save(update_fields=['last_activity', 'modified_at'])
            return user, False
        except cls.DoesNotExist:
            pass
        
        # Create new user
        user = cls.objects.create(
            anonymous_id=anonymous_session_id,  # Use session ID as anonymous ID for now
            current_anonymous_session_id=anonymous_session_id,
            last_activity=timezone.now()
        )
        
        return user, True
    
    def update_session_id(self, new_session_id):
        """
        Update the current session ID for this user.
        
        Args:
            new_session_id: New session ID from NGINX
        """
        from django.utils import timezone
        
        self.current_anonymous_session_id = new_session_id
        self.last_activity = timezone.now()
        self.save(update_fields=['current_anonymous_session_id', 'last_activity', 'modified_at'])
