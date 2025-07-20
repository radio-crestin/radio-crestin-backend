import json

from django.contrib.admin.options import BaseModelAdmin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.admin.widgets import AutocompleteSelect

from .middleware import get_request_cache, set_request_cache


class SmartSelectAutocompleteJsonView(AutocompleteJsonView):
    def get_queryset(self):
        """Return queryset based on ModelAdmin.get_search_results()."""
        qs = self.model_admin.get_queryset(self.request)
        qs = qs.complex_filter(self.source_field.get_limit_choices_to())
        qs, search_use_distinct = self.model_admin.get_search_results(
            self.request, qs, self.term
        )
        filters = json.loads(self.request.GET.get('filters', '{}'))

        qs = qs.filter(**filters)

        if search_use_distinct:
            qs = qs.distinct()
        return qs


class CachedAutocompleteSelect(AutocompleteSelect):
    def optgroups(self, name, value, attr=None):
        """Return selected options based on the ModelChoiceIterator."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {
            str(v) for v in value if str(v) not in self.choices.field.empty_values
        }
        if not self.is_required and not self.allow_multiple_selected:
            default[1].append(self.create_option(name, "", "", False, 0))
        remote_model_opts = self.field.remote_field.model._meta
        to_field_name = getattr(
            self.field.remote_field, "field_name", remote_model_opts.pk.attname
        )
        to_field_name = remote_model_opts.get_field(to_field_name).attname

        cache_key = f'cached_autocomplete_select_{self.field.cache_name}'
        cached_options = get_request_cache(cache_key)
        if not cached_options:
            cached_options = self.choices.queryset.using(self.db)
            set_request_cache(cache_key, cached_options)

        choices = (
            (getattr(obj, to_field_name), self.choices.field.label_from_instance(obj))
            for obj in cached_options
            if str(getattr(obj, to_field_name)) in list(selected_choices)
        )

        for option_value, option_label in choices:
            selected = str(option_value) in value and (
                    has_selected is False or self.allow_multiple_selected
            )
            has_selected |= selected
            index = len(default[1])
            subgroup = default[1]
            subgroup.append(
                self.create_option(
                    name, option_value, option_label, selected_choices, index
                )
            )
        return groups


class CachedAutocompleteForeignKeyMixins(BaseModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if "widget" not in kwargs:
            if db_field.name in self.get_autocomplete_fields(request):
                db = kwargs.get("using")
                kwargs["widget"] = CachedAutocompleteSelect(
                    db_field, self.admin_site, using=db
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
