from django.db import models
from django.utils.translation import gettext_lazy as _

from .forms import Form


class FormSubmission(models.Model):
    """One device's answers to a form: {question_id: value}."""

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='submissions')
    device_id = models.CharField(_("Device ID"), max_length=512, blank=True, default='')
    platform = models.CharField(_("Platform"), max_length=32, blank=True, default='')
    app_version = models.CharField(_("App version"), max_length=64, blank=True, default='')
    locale = models.CharField(_("Locale"), max_length=64, blank=True, default='')
    country = models.CharField(_("Country"), max_length=2, blank=True, default='')
    answers = models.JSONField(_("Answers"), default=dict)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'form_submissions'
        ordering = ('-created_at',)
        verbose_name = _("Form Submission")
        verbose_name_plural = _("Form Submissions")
        indexes = [models.Index(fields=['form', 'device_id'], name='form_submission_device_idx')]

    def __str__(self):
        return f"{self.form_id} · {self.device_id}"
