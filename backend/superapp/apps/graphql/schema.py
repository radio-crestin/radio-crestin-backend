import importlib
import os
import traceback
from typing import List, Type

import strawberry
from django.apps import apps
from django.db import connection
from strawberry.extensions import Extension, ParserCache
from strawberry.tools import merge_types
from strawberry.types.base import TypeDefinition
from strawberry_django.extensions.django_validation_cache import DjangoValidationCache
from strawberry_django.optimizer import DjangoOptimizerExtension

from .graphql.query_cache import QueryCache


class SQLPrintingExtension(Extension):
    def on_request_end(self):
        for query in connection.queries:
            print(f"Query: {query['sql']}")
            print(f"Time: {query['time']}")
            print("---")


class GraphQLExceptionHandlingExtension(Extension):
    def on_operation_end(self):
        # Check if there are any errors in the execution context
        if hasattr(self.execution_context, 'errors') and self.execution_context.errors:
            for error in self.execution_context.errors:
                print(f"GraphQL Error: {error}")
                if hasattr(error, '__cause__') and error.__cause__:
                    print("Exception traceback:")
                    traceback.print_exception(type(error.__cause__), error.__cause__, error.__cause__.__traceback__)
                elif hasattr(error, 'original_error') and error.original_error:
                    print("Exception traceback:")
                    traceback.print_exception(type(error.original_error), error.original_error, error.original_error.__traceback__)
                else:
                    # Try to get the traceback from the error itself
                    print("Exception traceback:")
                    traceback.print_exc()
                print("---")


def import_field_types():
    """Import all field_type.py files from installed apps to register custom field types"""
    for app_config in apps.get_app_configs():
        app_path = app_config.path
        field_type_path = os.path.join(app_path, 'graphql', 'field_type.py')

        # Import field_type module if it exists
        if os.path.exists(field_type_path):
            importlib.import_module(f"{app_config.name}.graphql.field_type")


def find_graphql_modules() -> tuple[List[Type], List[Type]]:
    """Find all Query and Mutation classes from installed apps"""
    queries = []
    mutations = []

    for app_config in apps.get_app_configs():
        app_path = app_config.path
        queries_path = os.path.join(app_path, 'graphql', 'queries.py')
        mutations_path = os.path.join(app_path, 'graphql', 'mutations.py')

        # Import queries module if it exists
        if os.path.exists(queries_path):
            queries_module = importlib.import_module(f"{app_config.name}.graphql.queries")
            if hasattr(queries_module, "Query"):
                queries.append(getattr(queries_module, "Query"))

        # Import mutations module if it exists
        if os.path.exists(mutations_path):
            mutations_module = importlib.import_module(f"{app_config.name}.graphql.mutations")
            if hasattr(mutations_module, "Mutation"):
                mutations.append(getattr(mutations_module, "Mutation"))

    return queries, mutations


def combine_types(base_class_name: str, types: List[Type]) -> Type:
    """Combine multiple strawberry types into one"""
    if not types:
        return None

    # Create a new type with combined fields
    combined_fields = {}
    for type_ in types:
        type_def: TypeDefinition = type_._type_definition
        for field in type_def.fields:
            combined_fields[field.python_name] = field

    return strawberry.type(
        type(
            base_class_name,
            (),
            combined_fields
        )
    )


# Import all field types first
import_field_types()

# Find and combine all queries and mutations
all_queries, all_mutations = find_graphql_modules()

# Create root types with Hasura-compatible names
query_root = merge_types(
    "query_root",
    tuple(all_queries)
)
mutation_root = merge_types(
    "mutation_root", 
    tuple(all_mutations)
)

# Also create standard names for compatibility
Query = query_root
Mutation = mutation_root

from strawberry.schema.config import StrawberryConfig

# Import directives for Hasura compatibility
try:
    from superapp.apps.radio_crestin.graphql.directives import cached
    directives = [cached]
except ImportError:
    directives = []

schema = strawberry.Schema(
    query=query_root,
    mutation=mutation_root,
    directives=directives,
    config=StrawberryConfig(
        auto_camel_case=False,  # Keep snake_case field names
    ),
    extensions=[
        QueryCache(
            default_timeout=300,  # 5 minutes default
            stale_while_revalidate=60,  # 1 minute stale tolerance
            cache_key_prefix="graphql_query_cache",
            enable_cache_control=True,
            max_query_depth=10,
        ),
        DjangoValidationCache(
            timeout=7 * 24 * 60 * 60,  # Cache for 7 days
        ),
        ParserCache(maxsize=1000),
        DjangoOptimizerExtension(
            enable_only_optimization = False, # This is creating a problem with django_multitenant
            enable_select_related_optimization = True,
            enable_prefetch_related_optimization = True,
            enable_annotate_optimization = True,
            enable_nested_relations_prefetch = True,
            execution_context = None,
            prefetch_custom_queryset = True,
        ),
        SQLPrintingExtension,
        GraphQLExceptionHandlingExtension,
    ]
)

