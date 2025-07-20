
from django.core.exceptions import ValidationError
from django.db import models

from .db_fields import ChainedForeignKey


class SuperAppBaseModel(models.Model):
    def clean(self):
        super().clean()
        for field in self._meta.fields:
            if isinstance(field, ChainedForeignKey):
                computed_filters = {}
                if field.dynamic_filters:
                    for key, config in field.filters.items():
                        computed_filters[key] = getattr(self, config).pk or None
                else:
                    computed_filters = field.filters
                if not field.remote_field.model.objects.filter(**{
                    **computed_filters,
                    'pk': getattr(self, field.name).pk or None
                }).exists():
                    raise ValidationError(
                        {
                            field.name: ValidationError(
                                f"Invalid config for {field.name}",
                                code='invalid'
                            )
                        }
                    )

    class Meta:
        abstract = True
