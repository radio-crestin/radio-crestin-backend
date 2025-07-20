from django.shortcuts import redirect
from django.urls import path, include

from superapp.apps.admin_portal.autocomplete import SmartSelectAutocompleteJsonView


def extend_superapp_urlpatterns(main_urlpatterns):
    from .sites import superapp_admin_site
    main_urlpatterns += [
        path("", lambda request: redirect('admin:index'), name="homepage"),
        path("i18n/", include("django.conf.urls.i18n")),
        path('portal/', include('massadmin.urls'), kwargs={'admin_site': superapp_admin_site}),
        path("portal/autocomplete/", SmartSelectAutocompleteJsonView.as_view(admin_site=superapp_admin_site), name="smart-select-autocomplete"),
        path("portal/", superapp_admin_site.urls),
    ]


def extend_superapp_admin_urlpatterns(main_admin_urlpatterns):
    main_admin_urlpatterns += [
    ]
