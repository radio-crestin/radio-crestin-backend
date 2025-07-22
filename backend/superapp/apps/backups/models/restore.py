from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from superapp.apps.backups.models.backup import Backup
from superapp.apps.backups.storage import PrivateBackupStorage

# Conditional imports for multi-tenant support
try:
    from django_multitenant.fields import TenantForeignKey
    from superapp.apps.multi_tenant.models import AppAwareTenantModel
    from superapp.apps.multi_tenant.utils import get_tenant_model_name

    MULTI_TENANT_ENABLED = True
    tenant_model_name = get_tenant_model_name()
    BaseModel = AppAwareTenantModel
except ImportError:
    MULTI_TENANT_ENABLED = False
    tenant_model_name = None
    BaseModel = models.Model


class RestoreTypeChoices:
    """
    A callable class to provide backup type choices from Django settings.
    This allows choices to be re-evaluated at runtime when needed.
    """
    def __iter__(self):
        backup_types = getattr(settings, 'BACKUPS', {}).get('BACKUP_TYPES', {})
        for key, backup_type in backup_types.items():
            yield key, backup_type['name']


class Restore(BaseModel):
    name = models.CharField(_("Name"), max_length=100, null=True, blank=True)
    file = models.FileField(
        _("File"),
        storage=PrivateBackupStorage,
        upload_to='restores/',
        blank=True,
        null=True,
    )
    backup = models.ForeignKey(
        Backup,
        on_delete=models.SET_NULL,
        related_name='restores',
        blank=True,
        null=True,
        verbose_name=_("Backup"),
        help_text=_("Optional. If selected, backup file path will override the file field.")
    )
    type = models.CharField(
        _("Restore Type"),
        max_length=50,
        choices=RestoreTypeChoices(),
        default='all_models'
    )
    cleanup_existing_data = models.BooleanField(_("Cleanup existing data"), default=False)
    done = models.BooleanField(_("Done"), default=False)

    started_at = models.DateTimeField(_("Started at"), blank=True, null=True)
    finished_at = models.DateTimeField(_("Finished at"), blank=True, null=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    if MULTI_TENANT_ENABLED:
        class TenantMeta:
            tenant_field_name = "tenant_id"

    class Meta:
        verbose_name = _("Restore")
        verbose_name_plural = _("Restores")
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.backup:
            if not self.file:
                self.file = self.backup.file
        if not self.file:
            raise ValueError("File or backup must be provided.")
        super().save(*args, **kwargs)

    def __str__(self):
        if MULTI_TENANT_ENABLED and hasattr(self, 'tenant'):
            return f"{self.name} ({self.tenant} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''})"
        else:
            return f"{self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''}"


# Dynamically add tenant field if multi-tenant is enabled
if MULTI_TENANT_ENABLED:
    Restore.add_to_class('tenant', TenantForeignKey(
        tenant_model_name,
        on_delete=models.SET_NULL,
        related_name='restores',
        blank=True,
        null=True,
    ))
