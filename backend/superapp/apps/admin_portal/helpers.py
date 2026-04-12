from django.contrib.admin import helpers
from django.contrib.admin.utils import lookup_field
from django.core.exceptions import ObjectDoesNotExist

# Keep exporting these classes for backwards compatibility
from .admin import SuperAppModelAdmin
from .models import SuperAppBaseModel as BaseModel

__all__ = ['SuperAppModelAdmin', 'BaseModel',]


# Try unfold's AdminReadonlyField, fall back to Django's
try:
    from unfold.admin import UnfoldAdminReadonlyField as _BaseReadonlyField
except ImportError:
    _BaseReadonlyField = helpers.AdminReadonlyField


class SuperAppAdminReadonlyField(_BaseReadonlyField):
    def is_custom_html_field(self) -> bool:
        field, obj, model_admin = (
            self.field["field"],
            self.form.instance,
            self.model_admin,
        )

        try:
            f, attr, config = lookup_field(field, obj, model_admin)
        except (AttributeError, ValueError, ObjectDoesNotExist):
            return False

        return hasattr(attr, 'custom_html_field') and attr.custom_html_field == True


helpers.AdminReadonlyField = SuperAppAdminReadonlyField

