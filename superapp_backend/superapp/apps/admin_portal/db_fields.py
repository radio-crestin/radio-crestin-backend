from django.db.models import ForeignKey


class ChainedForeignKey(ForeignKey):
    """
    A ForeignKey field that supports chained filtering of related objects.
    
    The filters and dynamic_filters parameters accept any valid Django filter expressions
    that can be passed to QuerySet.filter(). This includes:
    - Exact matches: {'field': value}
    - Lookups: {'field__gt': value, 'field__contains': value}
    - Q objects for complex queries
    - Related field lookups: {'related_field__field': value}
    
    Example usage:
    
    class MyModel(models.Model):
        foreingkey_field_1 = models.ForeignKey(
            'MyForeingModel',
            on_delete=models.PROTECT,
            blank=True,
            null=True,
        )
        field_2 = ChainedForeignKey(
            'MyOptionsModel',
            on_delete=models.PROTECT,
            blank=True,
            null=True,
            related_name='default_organization_profiles',
            filters={
                "is_visible": True,
            },
            dynamic_filters={
                "option_foreingkey_field_1": "foreingkey_field_1",
            }
        )

    class MyOptionsModel(models.Model):
        is_visible = models.BooleanField(default=True)
        option_foreingkey_field_1 = models.ForeignKey(
            'MyForeingModel',
            on_delete=models.PROTECT,
            blank=True,
            null=True,
        )
    
    In this example:
    - field_2 will only show MyOptionsModel instances where is_visible=True
    - field_2 will be dynamically filtered based on the value of foreingkey_field_1
    - The dynamic filter will be applied as {"option_foreingkey_field_1": "<<value of foreingkey_field_1>>"}
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the ChainedForeignKey field.
        
        Args:
            filters (dict): Static filters to apply to the queryset. Can use any valid Django
                filter expression including lookups, Q objects, and related field queries.
            dynamic_filters (dict|bool): Dynamic filters to apply based on other field values.
                If True, uses default dynamic filtering behavior.
                If False, disables dynamic filtering.
                If dict, maps local field names to related model field names. Supports
                the same filter expressions as the filters parameter.
            automatically_select_unique_choice (bool): If True and only one choice is available,
                automatically select it.
        """
        self.filters = kwargs.pop('filters', {})
        self.dynamic_filters = kwargs.pop('dynamic_filters', {})
        self.automatically_select_unique_choice = kwargs.pop('automatically_select_unique_choice', False)
        super().__init__(*args, **kwargs)
