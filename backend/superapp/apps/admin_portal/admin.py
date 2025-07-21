import copy
from typing import List, Optional, Dict, Any, Union

from admin_confirm import AdminConfirmMixin
from django.db import models
from django.db.models import ForeignKey
from django.forms import ModelChoiceField
from django.http import HttpRequest
from django.urls import reverse, URLPattern, path
from django.utils.text import wrap
from django_svelte_jsoneditor.widgets import SvelteJSONEditorWidget
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.dataclasses import UnfoldAction
from unfold.widgets import UnfoldBooleanSwitchWidget, UnfoldAdminFileFieldWidget

from .autocomplete import CachedAutocompleteForeignKeyMixins
from .db_fields import ChainedForeignKey
from .widgets import ChainedAdminSelect


class SuperAppModelAdmin(AdminConfirmMixin, ModelAdmin, ImportExportModelAdmin):
    actions_hidden = ()
    formfield_overrides = {
        # models.TextField: {
        #     "widget": WysiwygWidget,
        # },
        models.JSONField: {
            "widget": SvelteJSONEditorWidget,
        },
        models.FileField: {
            "widget": UnfoldAdminFileFieldWidget,
        },

    }

    def formfield_for_foreignkey(
            self, db_field: ForeignKey, request: HttpRequest, **kwargs
    ) -> Optional[ModelChoiceField]:
        db = kwargs.get("using")

        if isinstance(db_field, ChainedForeignKey):
            kwargs["widget"] = ChainedAdminSelect(
                db_field, self.admin_site, using=db
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        custom_html_fields = [
            attr for attr in dir(self)
            if hasattr(getattr(self, attr), 'custom_html_field') and getattr(self, attr).custom_html_field == True
        ]

        return tuple(readonly_fields) + tuple(custom_html_fields)

    def get_actions_hidden(self, request: HttpRequest) -> List[UnfoldAction]:
        return self._filter_unfold_actions_by_permissions(
            request, self._get_base_actions_hidden()
        )

    def _get_base_actions_hidden(self) -> List[UnfoldAction]:
        """
        Returns all available detail actions, prior to any filtering
        """
        return [self.get_unfold_action(action) for action in self.actions_hidden or []]

    def get_actions_detail(
            self, request: HttpRequest, object_id: Optional[Union[int, str]] = None
    ) -> List[UnfoldAction]:
        return self._filter_unfold_actions_by_permissions(
            request, self._get_base_actions_detail(), object_id
        )

    def get_actions_submit_line(
            self, request: HttpRequest, object_id: Optional[Union[int, str]] = None
    ) -> List[UnfoldAction]:
        return self._filter_unfold_actions_by_permissions(
            request, self._get_base_actions_submit_line(), object_id
        )

    def changeform_view(
            self,
            request: HttpRequest,
            object_id: Optional[str] = None,
            form_url: str = "",
            extra_context: Optional[Dict[str, bool]] = None,
    ) -> Any:
        if extra_context is None:
            extra_context = {}

        new_formfield_overrides = copy.deepcopy(self.formfield_overrides)
        new_formfield_overrides.update(
            {models.BooleanField: {"widget": UnfoldBooleanSwitchWidget}}
        )

        self.formfield_overrides = new_formfield_overrides

        actions = []
        if object_id:
            for action in self.get_actions_detail(request, object_id=object_id):
                actions.append(
                    {
                        "title": action.description,
                        "attrs": action.method.attrs,
                        "path": reverse(
                            f"admin:{action.action_name}", args=(object_id,)
                        ),
                    }
                )
            for action in self.get_actions_hidden(request):
                actions.append(
                    {
                        "title": action.description,
                        "attrs": action.method.attrs,
                        "path": reverse(
                            f"admin:{action.action_name}", args=(object_id,)
                        ),
                    }
                )

        extra_context.update(
            {
                "actions_submit_line": self.get_actions_submit_line(request,
                                                                    object_id=object_id if object_id is not None else None),
                "actions_detail": actions,
            }
        )

        return super().changeform_view(request, object_id, form_url, extra_context)

    def get_urls(self) -> List[URLPattern]:
        urls = super().get_urls()

        action_hidden_urls = [
            path(
                f"<path:object_id>/{action.path}/",
                wrap(action.method),
                name=action.action_name,
            )
            for action in self._get_base_actions_hidden()
        ]
        return urls + action_hidden_urls

    def get_changelist(self, request, **kwargs):
        """
        Return the ChangeList class for use on the changelist page.
        """
        from django.contrib.admin.views.main import ChangeList

        return ChangeList

    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        inline_formsets = super().get_inline_formsets(request, formsets, inline_instances, obj)
        for inline, formset in zip(inline_instances, inline_formsets):
            if hasattr(inline, 'display_copy_action'):
                formset.display_copy_action = inline.display_copy_action
            if hasattr(inline, 'display_paste_action'):
                formset.display_paste_action = inline.display_paste_action
        return inline_formsets


def superapp_model_admin_factory(name, argnames, base_class=SuperAppModelAdmin):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # here, the argnames variable is the one passed to the
            # ClassFactory call
            if key not in argnames:
                raise TypeError("Argument %s not valid for %s"
                                % (key, self.__class__.__name__))
            setattr(self, key, value)
        base_class.__init__(self, name[:-len("Class")])

    newclass = type(name, (base_class,), {"__init__": __init__})
    return newclass


class SuperAppTabularInline(CachedAutocompleteForeignKeyMixins, TabularInline):
    class Media:
        js = ('admin_portal/js/tabular_inlie_import_export.js',)


class SuperAppStackedInline(CachedAutocompleteForeignKeyMixins, StackedInline):
    pass
