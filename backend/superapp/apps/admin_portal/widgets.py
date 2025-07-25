import json

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AutocompleteSelect
from django.forms import Widget, TextInput
from django.template.loader import render_to_string


class ChainedAdminSelect(AutocompleteSelect):
    def build_attrs(self, base_attrs, extra_attrs=None):
        """
        Set select2's AJAX attributes.

        Attributes can be set using the html5 data attribute.
        Nested attributes require a double dash as per
        https://select2.org/configuration/data-attributes#nested-subkey-options
        """
        attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)
        attrs.setdefault("class", "")
        attrs.update(
            {
                "data-ajax--cache": "true",
                "data-ajax--delay": 250,
                "data-ajax--type": "GET",
                "data-ajax--url": self.get_url(),
                "data-app-label": self.field.model._meta.app_label,
                "data-model-name": self.field.model._meta.model_name,
                "data-field-name": self.field.name,
                "data-theme": "admin-autocomplete",
                "data-allow-clear": json.dumps(not self.is_required),
                "data-placeholder": "",  # Allows clearing of the input.
                "data-dynamic-filters": json.dumps(self.field.dynamic_filters),
                "data-automatically-select-unique-choice": json.dumps(self.field.automatically_select_unique_choice),
                "data-filters": json.dumps(self.field.filters),
                "lang": self.i18n_name,
                "class": (
                        attrs["class"]
                        + (" " if attrs["class"] else "")
                        + "admin-autocomplete"
                ).replace("admin-autocomplete", "admin-autocomplete-chained"),
            }
        )
        return attrs

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        i18n_file = (
            ("admin/js/vendor/select2/i18n/%s.js" % self.i18n_name,)
            if self.i18n_name
            else ()
        )
        return forms.Media(
            js=(
                   "admin/js/vendor/jquery/jquery%s.js" % extra,
                   "admin/js/vendor/select2/select2.full%s.js" % extra,
               )
               + i18n_file
               + (
                   "admin/js/jquery.init.js",
                   "admin_portal/js/autocomplete.chained.js",
               ),
            css={
                "screen": (
                    "admin/css/vendor/select2/select2%s.css" % extra,
                    "admin/css/autocomplete.css",
                ),
            },
        )


class PasswordToggleWidget(TextInput):
    """
    A widget that displays a password field with a toggle button to show/hide the password.
    Uses Tailwind CSS for styling and includes a button to toggle password visibility.
    """
    template_name = 'admin/password_toggle_widget.html'
    
    class Media:
        js = ('admin_portal/js/password_toggle.js',)
        
    def __init__(self, attrs=None, render_value=False):
        super().__init__(attrs)
        self.render_value = render_value
        
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['type'] = 'password'
        # We don't need to add classes here since they're directly in the template
        return context

