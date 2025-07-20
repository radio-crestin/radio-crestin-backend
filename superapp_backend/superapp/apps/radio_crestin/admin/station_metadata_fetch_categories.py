from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationMetadataFetchCategories


@admin.register(StationMetadataFetchCategories, site=superapp_admin_site)
class StationMetadataFetchCategoriesAdmin(SuperAppModelAdmin):
    list_display = ['slug', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['slug']
    readonly_fields = ['created_at', 'updated_at']