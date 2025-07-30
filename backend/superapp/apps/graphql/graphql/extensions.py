from __future__ import annotations

from strawberry.extensions import SchemaExtension


class CacheControlExtension(SchemaExtension):
    """Extension to set HTTP cache control headers based on GraphQL field directives"""

    def __init__(self):
        super().__init__()
        self.cache_control_config = {}

    def on_executing_start(self):
        """Extract cache control metadata when execution starts"""
        self.cache_control_config = {}
        self._collect_cache_control_metadata()

    def on_executing_end(self):
        """Set cache control headers when execution ends"""
        if self.cache_control_config:
            self._set_cache_headers()

    def _collect_cache_control_metadata(self):
        """Collect cache control metadata from field resolvers"""
        operation = self.execution_context._get_first_operation()
        if not operation:
            return

        # Check root field resolvers for cache control metadata
        for field_node in operation.selection_set.selections:
            if hasattr(field_node, 'name'):
                field_name = field_node.name.value
                resolver = self._get_field_resolver(field_name)
                if resolver and hasattr(resolver, '_cache_control_metadata'):
                    metadata = getattr(resolver, '_cache_control_metadata')
                    self._merge_metadata(metadata)

    def _get_field_resolver(self, field_name):
        """Get resolver for a field"""
        try:
            schema = self.execution_context.schema
            operation_type = self.execution_context.operation_type
            if not operation_type:
                return None

            if operation_type.name.lower() == 'query':
                root_type = getattr(schema, 'query_type', None)
            elif operation_type.name.lower() == 'mutation':
                root_type = getattr(schema, 'mutation_type', None)
            else:
                return None

            if root_type and hasattr(root_type, '_type_definition'):
                type_def = root_type._type_definition
                if hasattr(type_def, field_name):
                    field = getattr(type_def, field_name)
                    return getattr(field, 'resolver', None)
        except (AttributeError, TypeError):
            return None
        return None

    def _merge_metadata(self, metadata):
        """Merge cache control metadata using most restrictive values"""
        if not self.cache_control_config:
            self.cache_control_config = dict(metadata)
        else:
            # Use minimum max_age (most restrictive)
            if metadata.get('max_age') is not None:
                current = self.cache_control_config.get('max_age')
                if current is None or metadata['max_age'] < current:
                    self.cache_control_config['max_age'] = metadata['max_age']

            # Override with more restrictive flags
            if metadata.get('no_cache'):
                self.cache_control_config['no_cache'] = True
            if metadata.get('private'):
                self.cache_control_config['private'] = True

    def _set_cache_headers(self):
        """Set HTTP cache control headers"""
        try:
            request = getattr(self.execution_context, 'request', None)
            if not request:
                return

            # Build cache control header
            parts = []

            if self.cache_control_config.get('no_cache'):
                parts.append('no-cache')
            else:
                max_age = self.cache_control_config.get('max_age')
                if max_age is not None:
                    parts.append(f'max-age={max_age}')

            if self.cache_control_config.get('private'):
                parts.append('private')
            elif self.cache_control_config.get('public'):
                parts.append('public')

            if parts and hasattr(request, 'META'):
                # Store for Django response middleware to pick up
                request.META['HTTP_CACHE_CONTROL'] = ', '.join(parts)
        except (AttributeError, TypeError, KeyError) as e:
            # Log the specific error if needed for debugging
            pass
