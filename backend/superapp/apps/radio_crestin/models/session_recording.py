from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class SessionRecordingConfig(models.Model):
    """Global session-replay rollout config (single row).

    The mobile app asks the backend, per device, whether it should record its
    screen (PostHog session replay). This row holds the master switch and the
    rollout percentage, so the rollout can change without an app release.
    """

    enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enabled"),
        help_text=_("Master switch. When off, only manual force-on overrides record."),
    )
    rollout_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Rollout percentage"),
        help_text=_("Percent of devices (0-100) that record, chosen deterministically by device id."),
    )
    sample_rate = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_("Sample rate"),
        help_text=_("PostHog sample rate (0.0-1.0) within recorded sessions. Usually 1.0."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'session_recording_config'
        verbose_name = _("Session Recording Config")
        verbose_name_plural = _("Session Recording Config")

    def __str__(self):
        state = 'on' if self.enabled else 'off'
        return f"Session recording: {state} @ {self.rollout_percentage}%"


class SessionRecordingOverride(models.Model):
    """Per-device manual override for session replay.

    Add a device id here to force recording on or off for that device,
    regardless of the rollout percentage — handy for test devices.
    """

    device_id = models.CharField(
        max_length=512,
        unique=True,
        verbose_name=_("Device ID"),
        help_text=_("The device's anonymous id (the device_id the app sends)."),
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name=_("Record"),
        help_text=_("Force recording ON (checked) or OFF (unchecked) for this device."),
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Note"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'session_recording_override'
        verbose_name = _("Session Recording Override")
        verbose_name_plural = _("Session Recording Overrides")

    def __str__(self):
        state = 'on' if self.enabled else 'off'
        return f"{self.device_id}: {state}"
