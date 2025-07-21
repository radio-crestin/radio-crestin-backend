from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from superapp.apps.backups.models.backup import Backup
from superapp.apps.backups.tasks.backup import process_backup
import unfold.decorators
from django.utils.translation import gettext_lazy as _


@admin.register(Backup, site=superapp_admin_site)
class BackupAdmin(SuperAppModelAdmin):
    list_display = ['name', 'created_at', 'type', 'file', 'done']
    list_filter = ['created_at', 'type', 'done']
    search_fields = ['name', 'created_at', 'file']
    autocomplete_fields = ['tenant']
    actions = []
    actions_detail = [
        "retry_backup",
    ]

    def get_fields(self, request, obj=None):
        """
        Only show the tenant and type fields when adding a new backup.
        Show all fields when editing an existing backup.
        """
        if obj is None:  # Adding a new object
            return ['name', 'tenant', 'type']
        # Editing an existing object
        return ['name', 'tenant', 'type', 'file', 'done', 'started_at', 'finished_at', 'created_at', 'updated_at']

    def get_readonly_fields(self, request, obj=None):
        """
        Make all fields except 'tenant' readonly when adding a new backup.
        For existing backups, all fields are readonly.
        """
        if obj is None:  # Adding a new object
            return []
        # Editing an existing object
        return ['name', 'tenant', 'type', 'created_at', 'updated_at', 'file', 'done', 'started_at', 'finished_at']

    @unfold.decorators.action(description=_("Retry Backup"))
    def retry_backup(self, request, object_id: int):
        """
        Detail action to retry the backup process synchronously and raise any errors directly.
        """
        try:
            backup = Backup.objects.get(pk=object_id)
            # Call the process_backup function directly (not as a Celery task)
            # This will execute synchronously and raise any exceptions directly
            process_backup.apply(args=[backup.pk])
            messages.success(request, f"Backup '{backup.name}' was successfully processed.")
        except Exception as e:
            # Capture and display the error directly to the user
            messages.error(request, f"Error processing backup: {str(e)}")
            if settings.DEBUG:
                raise e

        return redirect(
            reverse_lazy("admin:backups_backup_change", args=(object_id,))
        )

    def save_model(self, request, obj, form, change):
        """
        Set a default name for the backup if one is not provided.
        Format: "Backup YYYY-MM-DD HH:MM:SS"
        """
        if not obj.name:  # If name is None or empty
            # Format the current datetime
            current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            obj.name = f"Backup {current_time}"

        super().save_model(request, obj, form, change)
