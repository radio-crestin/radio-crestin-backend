from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from superapp.apps.backups.models.restore import Restore
from superapp.apps.backups.tasks.restore import process_restore
import unfold.decorators
from django.utils.translation import gettext_lazy as _


@admin.register(Restore, site=superapp_admin_site)
class RestoreAdmin(SuperAppModelAdmin):
    list_display = ['name', 'created_at', 'file', 'backup', 'done']
    list_filter = ['created_at', 'done']
    search_fields = ['name', 'created_at', 'file']
    autocomplete_fields = ['tenant', 'backup']
    actions = []
    actions_detail = [
        "retry_restore",
    ]

    def get_fields(self, request, obj=None):
        """
        Only show certain fields when adding a new restore.
        Show all fields when editing an existing restore.
        """
        if obj is None:  # Adding a new object
            return ['name', 'tenant', 'file', 'backup', 'type', 'cleanup_existing_data']
        # Editing an existing object
        return ['name', 'tenant', 'file', 'backup', 'done', 'started_at', 'finished_at', 'created_at', 'updated_at']

    def get_readonly_fields(self, request, obj=None):
        """
        Make all fields except specific ones readonly when editing an existing restore.
        """
        if obj is None:  # Adding a new object
            return []
        # Editing an existing object
        return ['name', 'tenant', 'type', 'file', 'backup', 'created_at', 'updated_at', 'done', 'started_at', 'finished_at', 'cleanup_existing_data']

    @unfold.decorators.action(description=_("Retry Restore"))
    def retry_restore(self, request, object_id: int):
        """
        Detail action to retry the restore process synchronously and raise any errors directly.
        """
        try:
            restore = Restore.objects.get(pk=object_id)
            # Call the process_restore function directly (not as a Celery task)
            # This will execute synchronously and raise any exceptions directly
            process_restore.apply(args=[restore.pk])
            messages.success(request, f"Restore '{restore.name}' was successfully processed.")
        except Exception as e:
            # Capture and display the error directly to the user
            messages.error(request, f"Error processing restore: {str(e)}")
            if settings.DEBUG:
                raise e

        return redirect(
            reverse_lazy("admin:backups_restore_change", args=(object_id,))
        )

    def save_model(self, request, obj, form, change):
        """
        Set a default name for the restore if one is not provided.
        Format: "Restore YYYY-MM-DD HH:MM:SS"
        """
        if not obj.name:  # If name is None or empty
            # Format the current datetime
            current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            obj.name = f"Restore {current_time}"

        super().save_model(request, obj, form, change)

