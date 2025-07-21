from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta


class ListeningSessions(models.Model):
    """
    Model to track user listening sessions for analytics.
    
    A session represents a continuous listening period for a user on a station.
    Sessions are separated by gaps of more than 5 minutes of inactivity.
    """
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    user = models.ForeignKey(
        'radio_crestin.AppUsers',
        verbose_name=_("App Users"),
        on_delete=models.CASCADE,
        related_name='listening_sessions'
    )

    station = models.ForeignKey(
        'Stations',
        verbose_name=_("Station"),
        on_delete=models.CASCADE,
        related_name='listening_sessions'
    )

    anonymous_session_id = models.CharField(
        _("Anonymous Session ID"), 
        max_length=512, 
        help_text=_("Anonymous session identifier from NGINX logs")
    )
    
    start_time = models.DateTimeField(_("Session start time"))
    end_time = models.DateTimeField(_("Session end time"), blank=True, null=True)
    last_activity = models.DateTimeField(_("Last activity"), help_text=_("Last time user activity was detected"))
    
    duration_seconds = models.IntegerField(
        _("Duration in seconds"), 
        default=0,
        help_text=_("Total session duration based on last_activity - start_time")
    )
    
    # Analytics data
    total_requests = models.IntegerField(_("Total requests"), default=0)
    bytes_transferred = models.BigIntegerField(_("Bytes transferred"), default=0)
    playlist_requests = models.IntegerField(_("Playlist requests"), default=0)
    segment_requests = models.IntegerField(_("Segment requests"), default=0)
    
    # User context
    ip_address = models.GenericIPAddressField(_("IP Address"), blank=True, null=True)
    user_agent = models.TextField(_("User Agent"), blank=True, null=True)
    referer = models.URLField(_("Referer"), blank=True, null=True)
    
    # Status tracking
    is_active = models.BooleanField(
        _("Is active"), 
        default=True,
        help_text=_("True if session had activity in the last 5 minutes")
    )
    
    # Additional data
    info = models.JSONField(_("Additional info"), blank=True, null=True)

    class Meta:
        managed = True
        verbose_name = _("Listening Session")
        verbose_name_plural = _("Listening Sessions")
        db_table = 'listening_sessions'
        ordering = ('-last_activity',)
        indexes = [
            models.Index(fields=['station', 'is_active', 'last_activity']),
            models.Index(fields=['user', 'station', 'last_activity']),
            models.Index(fields=['anonymous_session_id', 'station']),
            models.Index(fields=['is_active', 'last_activity']),
        ]

    def __str__(self):
        return f"Session: {self.user} - {self.station.title} - {self.start_time}"
    
    def update_activity(self, timestamp=None, bytes_sent=0, is_playlist=False):
        """
        Update session activity and calculate duration.
        
        Args:
            timestamp: Activity timestamp (default: now)
            bytes_sent: Bytes transferred in this request
            is_playlist: True if this was a playlist request
        """
        if timestamp is None:
            timestamp = timezone.now()
            
        self.last_activity = timestamp
        self.total_requests += 1
        self.bytes_transferred += bytes_sent
        
        if is_playlist:
            self.playlist_requests += 1
        else:
            self.segment_requests += 1
        
        # Calculate duration
        self.duration_seconds = int((self.last_activity - self.start_time).total_seconds())
        
        # Update active status
        self.is_active = True
        self.save(update_fields=[
            'last_activity', 'total_requests', 'bytes_transferred',
            'playlist_requests', 'segment_requests', 'duration_seconds', 
            'is_active', 'updated_at'
        ])
    
    def check_session_timeout(self, timeout_minutes=5):
        """
        Check if session has timed out and mark as inactive.
        
        Args:
            timeout_minutes: Timeout threshold in minutes (default: 5)
            
        Returns:
            True if session was marked inactive, False otherwise
        """
        if not self.is_active:
            return False
            
        timeout_threshold = timezone.now() - timedelta(minutes=timeout_minutes)
        
        if self.last_activity < timeout_threshold:
            self.is_active = False
            if not self.end_time:
                self.end_time = self.last_activity
            self.save(update_fields=['is_active', 'end_time', 'updated_at'])
            return True
            
        return False
    
    @classmethod
    def get_or_create_session(cls, user, station, anonymous_session_id, 
                             ip_address=None, user_agent=None, referer=None):
        """
        Get existing active session or create a new one.
        
        Args:
            user: AppUsers instance
            station: Station instance
            anonymous_session_id: Session ID from NGINX
            ip_address: User IP address
            user_agent: User agent string
            referer: HTTP referer
            
        Returns:
            Tuple of (session, created) where created is True for new sessions
        """
        timeout_threshold = timezone.now() - timedelta(minutes=5)
        
        # Try to find an existing active session
        try:
            session = cls.objects.get(
                user=user,
                station=station,
                anonymous_session_id=anonymous_session_id,
                is_active=True,
                last_activity__gte=timeout_threshold
            )
            return session, False
        except cls.DoesNotExist:
            pass
        
        # Create new session
        session = cls.objects.create(
            user=user,
            station=station,
            anonymous_session_id=anonymous_session_id,
            start_time=timezone.now(),
            last_activity=timezone.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            is_active=True
        )
        
        return session, True
    
    @classmethod
    def cleanup_inactive_sessions(cls, timeout_minutes=5):
        """
        Mark sessions as inactive if they haven't had activity within the timeout period.
        
        Args:
            timeout_minutes: Timeout threshold in minutes
            
        Returns:
            Number of sessions marked as inactive
        """
        timeout_threshold = timezone.now() - timedelta(minutes=timeout_minutes)
        
        inactive_sessions = cls.objects.filter(
            is_active=True,
            last_activity__lt=timeout_threshold
        )
        
        # Update end_time for sessions that don't have it set
        inactive_sessions.filter(end_time__isnull=True).update(
            end_time=models.F('last_activity')
        )
        
        # Mark as inactive
        count = inactive_sessions.update(is_active=False)
        
        return count
    
    @classmethod
    def get_active_listeners_count(cls, station=None, minutes=1):
        """
        Get count of unique active listeners.
        
        Args:
            station: Station instance (optional, for specific station)
            minutes: Activity window in minutes (default: 1 for last minute)
            
        Returns:
            Number of unique active listeners
        """
        activity_threshold = timezone.now() - timedelta(minutes=minutes)
        
        queryset = cls.objects.filter(
            is_active=True,
            last_activity__gte=activity_threshold
        )
        
        if station:
            queryset = queryset.filter(station=station)
            
        return queryset.values('user', 'anonymous_session_id').distinct().count()


