import importlib.util
from typing import Optional, Dict, Any, List

from django.contrib import admin
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.functional import Promise
from django_superapp.urls import extend_superapp_admin_urlpatterns
from unfold.settings import get_config
from unfold.sites import UnfoldAdminSite

from .forms import LoginForm


def _resolve_links(value):
    """A copy of a sidebar/tabs config with each lazy `link` (reverse_lazy) turned into its URL string.

    Callables (titles, permissions, link callbacks) are kept as they are.
    """
    if isinstance(value, dict):
        return {
            key: str(item) if key == 'link' and isinstance(item, Promise) else _resolve_links(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_links(item) for item in value]
    return value


class SuperAppAdminSite(UnfoldAdminSite):
    login_form = LoginForm
    # Unfold resolves every lazy sidebar and tab link again for every navigation item on every
    # page (~850 reverse() calls per page); the URLs never change, so resolve them once.
    RESOLVED_CONFIG_KEYS = ('SIDEBAR', 'TABS')

    def _get_config(self, key: str, *args):
        if key not in self.RESOLVED_CONFIG_KEYS:
            return super()._get_config(key, *args)
        resolved = self.__dict__.setdefault('_resolved_config', {})
        if key not in resolved:
            resolved[key] = _resolve_links(get_config(self.settings_name).get(key))
        value = resolved[key]
        return self._get_value(value, *args) if value else None

    def get_urls(self):
        main_admin_urlpatterns = []
        from ... import apps as superapp_apps
        extend_superapp_admin_urlpatterns(main_admin_urlpatterns, superapp_apps)
        urlpatterns = [
                          path(x["path"], self.custom_admin_page(x["view"]), name=x.get("name"))
                          for x in main_admin_urlpatterns
                      ] + super().get_urls()
        return urlpatterns

    def custom_admin_page(self, view):
        def generator(request: HttpRequest, extra_context: Optional[Dict[str, Any]] = None,
                      **kwargs) -> TemplateResponse:
            app_list = self.get_app_list(request)

            context = {
                **self.each_context(request),
                "title": self.index_title,
                "subtitle": None,
                "app_list": app_list,
                "index": True,
                **(extra_context or {}),
            }

            request.current_app = self.name

            view_instance = view.as_view()
            return view_instance(request, context, **kwargs)

        return generator

    def get_sidebar_list(self, request: HttpRequest) -> List[Dict[str, Any]]:
        super_sidebar_list = super().get_sidebar_list(request)
        # Do not display groups which are empty or the items permissions are false
        sidebar_list = []
        for sidebar in super_sidebar_list:
            sidebar_items = sidebar.get("items", [])
            sidebar_items = [item for item in sidebar_items if item.get("permission", lambda x: True)(request)]
            # check if item title is a callback and call it using request if it is
            sidebar_items = [
                {**item, "title": item["title"](request) if callable(item["title"]) else item["title"]}
                for item in sidebar_items
            ]
            if sidebar_items:
                sidebar_list.append({
                    **sidebar,
                    "items": sidebar_items
                })
        return sidebar_list


superapp_admin_site = SuperAppAdminSite()

if importlib.util.find_spec("allauth"):
    from allauth.account.decorators import secure_admin_login
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)
    superapp_admin_site.login = secure_admin_login(superapp_admin_site.login)
