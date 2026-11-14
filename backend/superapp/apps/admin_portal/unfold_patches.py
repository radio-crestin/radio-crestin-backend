"""Faster drop-ins for Unfold template helpers that showed up in admin page profiles."""
import json

from django.contrib.admin.utils import flatten_fieldsets
from django.forms import CheckboxSelectMultiple
from django.utils.safestring import mark_safe
from unfold.templatetags import unfold as unfold_tags
from unfold.widgets import UnfoldAdminMoneyWidget, UnfoldAdminSplitDateTimeWidget


def changeform_data(adminform) -> str:
    """The Alpine x-data of a change form with conditional_fields: every editable field, empty.

    Same output as Unfold's filter, read from the form's fields instead of building every admin
    field: Unfold's version also builds the readonly fields, which runs their display methods
    a second time on each page.
    """
    fields = {}
    for name in flatten_fieldsets(adminform.fieldsets):
        form_field = adminform.form.fields.get(name)
        if form_field is None:  # a readonly field
            continue
        widget = form_field.widget
        if isinstance(widget, (UnfoldAdminSplitDateTimeWidget, UnfoldAdminMoneyWidget)):
            for index in range(len(widget.widgets)):
                fields[f'{name}{widget.widgets_names[index]}'] = None
        elif isinstance(widget, CheckboxSelectMultiple):
            fields[name] = []
        else:
            fields[name] = None
    return mark_safe(json.dumps(fields))


def apply():
    # Templates resolve filters when they are parsed, so this runs in AppConfig.ready().
    unfold_tags.register.filters['changeform_data'] = changeform_data
