import json
import logging
import traceback
import sys
from typing import Any, Callable
from inspect import isawaitable

from strawberry.extensions import SchemaExtension
from graphql import GraphQLResolveInfo

from superapp.apps.posthog_error_tracking.utils import track_exception, track_event

logger = logging.getLogger(__name__)


class GraphQLExceptionHandlingExtension(SchemaExtension):
    """
    GraphQL extension that captures and reports all errors to PostHog
    """
    
    async def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> Any:
        """Wrap resolver execution to capture exceptions as they occur"""
        try:
            result = _next(root, info, *args, **kwargs)
            
            if isawaitable(result):
                result = await result
                
            return result
        except Exception as e:
            # Capture exception immediately when it occurs
            self._track_resolver_exception(e, info)
            # Re-raise to maintain GraphQL error handling behavior
            raise

    def on_operation_end(self):
        # Check if there are any errors in the execution context
        if hasattr(self.execution_context, 'errors') and self.execution_context.errors:
            # Get request data for context
            request = self.execution_context.context.request

            # Extract query information
            try:
                request_data = json.loads(request.body) if request.body else {}
                query = request_data.get('query', '')
                variables = request_data.get('variables', {})
                operation_name = request_data.get('operationName', '')
            except:
                query = 'Unknown query'
                variables = {}
                operation_name = ''

            for error in self.execution_context.errors:
                logger.debug(f"Processing GraphQL Error: {error}")
                logger.debug(f"Error Type: {type(error).__name__}")

                # Determine if this is an exception-based error
                has_exception = False
                exception_info = None

                # Try to extract exception information if available
                if hasattr(error, '__cause__') and error.__cause__:
                    has_exception = True
                    exception_info = error.__cause__
                elif hasattr(error, 'original_error') and error.original_error:
                    has_exception = True
                    exception_info = error.original_error
                else:
                    # Try to get any available traceback from current execution
                    exc_info = sys.exc_info()
                    if exc_info[0] is not None:
                        has_exception = True
                        exception_info = exc_info[1]

                # Build error context for PostHog
                error_context = {
                    'graphql_query': query[:500],  # Limit query length
                    'graphql_variables': json.dumps(variables) if variables else '{}',
                    'graphql_operation_name': operation_name,
                    'error_message': str(error),
                    'error_type': type(error).__name__,
                    'path': request.path,
                    'method': request.method,
                }

                # Add error-specific details
                if hasattr(error, 'message'):
                    error_context['error_detail_message'] = str(error.message)
                if hasattr(error, 'path'):
                    error_context['error_path'] = str(error.path)
                if hasattr(error, 'locations'):
                    error_context['error_locations'] = str(error.locations)
                if hasattr(error, 'extensions'):
                    error_context['error_extensions'] = json.dumps(error.extensions) if isinstance(error.extensions, dict) else str(error.extensions)

                # Determine user ID
                user_id = 'anonymous'
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user_id = str(request.user.id)

                try:
                    if has_exception and exception_info:
                        # Track as exception for errors with actual exceptions
                        error_context['error_category'] = 'graphql_exception'
                        track_exception(exception_info, error_context, user_id)
                    else:
                        # Track as event for non-exception errors (validation, field errors, etc.)
                        error_context['error_category'] = 'graphql_error'

                        # Create a synthetic exception for consistency
                        synthetic_exception = Exception(f"GraphQL {type(error).__name__}: {str(error)}")
                        track_exception(synthetic_exception, error_context, user_id)

                        # Also track as a separate event for better filtering
                        track_event(
                            user_id=user_id,
                            event_name='graphql_error',
                            properties=error_context
                        )
                except Exception as tracking_error:
                    logger.error(f"Failed to track GraphQL error to PostHog: {tracking_error}")
    
    def _track_resolver_exception(self, exception: Exception, info: GraphQLResolveInfo):
        """Track exceptions that occur during resolver execution"""
        try:
            request = self.execution_context.context.request
            
            # Extract query information
            try:
                request_data = json.loads(request.body) if request.body else {}
                query = request_data.get('query', '')
                variables = request_data.get('variables', {})
                operation_name = request_data.get('operationName', '')
            except:
                query = 'Unknown query'
                variables = {}
                operation_name = ''
            
            # Build field path information
            field_path = f"{info.parent_type}.{info.field_name}"
            graphql_path = ".".join(map(str, info.path.as_list()))
            
            # Build error context
            error_context = {
                'graphql_query': query[:500],  # Limit query length
                'graphql_variables': json.dumps(variables) if variables else '{}',
                'graphql_operation_name': operation_name,
                'error_message': str(exception),
                'error_type': type(exception).__name__,
                'error_category': 'graphql_resolver_exception',
                'path': request.path,
                'method': request.method,
                'field_name': info.field_name,
                'parent_type': info.parent_type.name,
                'field_path': field_path,
                'graphql_path': graphql_path,
            }
            
            # Get traceback
            tb = traceback.format_exc()
            error_context['traceback'] = tb
            
            # Determine user ID
            user_id = 'anonymous'
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = str(request.user.id)
            
            # Track the exception
            track_exception(exception, error_context, user_id)
            
            # Log for debugging
            logger.error(f"GraphQL resolver exception in {field_path}: {exception}")
            logger.debug(f"Exception traceback:\n{tb}")
            
        except Exception as tracking_error:
            logger.error(f"Failed to track resolver exception to PostHog: {tracking_error}")


class GraphQLExceptionHandlingExtensionSync(GraphQLExceptionHandlingExtension):
    """Synchronous version of the GraphQL exception handling extension"""
    
    def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> Any:
        """Wrap resolver execution to capture exceptions as they occur (sync version)"""
        try:
            return _next(root, info, *args, **kwargs)
        except Exception as e:
            # Capture exception immediately when it occurs
            self._track_resolver_exception(e, info)
            # Re-raise to maintain GraphQL error handling behavior
            raise


__all__ = ["GraphQLExceptionHandlingExtension", "GraphQLExceptionHandlingExtensionSync"]
