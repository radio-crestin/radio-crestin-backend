import json
import logging
import traceback
import sys

from strawberry.extensions import Extension

from superapp.apps.posthog_error_tracking.utils import track_exception, track_event

logger = logging.getLogger(__name__)


class GraphQLExceptionHandlingExtension(Extension):
    """
    GraphQL extension that captures and reports all errors to PostHog
    """
    
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
                print(f"GraphQL Error: {error}")
                print(f"Error Type: {type(error).__name__}")

                # Determine if this is an exception-based error
                has_exception = False
                exception_info = None
                
                # Try to print exception traceback if available
                if hasattr(error, '__cause__') and error.__cause__:
                    print("Exception traceback:")
                    traceback.print_exception(type(error.__cause__), error.__cause__, error.__cause__.__traceback__)
                    has_exception = True
                    exception_info = error.__cause__
                elif hasattr(error, 'original_error') and error.original_error:
                    print("Exception traceback:")
                    traceback.print_exception(type(error.original_error), error.original_error, error.original_error.__traceback__)
                    has_exception = True
                    exception_info = error.original_error
                else:
                    # For non-exception errors (validation, field errors, etc.)
                    print("Error details:")
                    if hasattr(error, 'message'):
                        print(f"  Message: {error.message}")
                    if hasattr(error, 'path'):
                        print(f"  Path: {error.path}")
                    if hasattr(error, 'locations'):
                        print(f"  Locations: {error.locations}")
                    if hasattr(error, 'extensions'):
                        print(f"  Extensions: {error.extensions}")

                    # Try to get any available traceback
                    import sys
                    exc_info = sys.exc_info()
                    if exc_info[0] is not None:
                        print("Current exception traceback:")
                        traceback.print_exc()
                        has_exception = True
                        exception_info = exc_info[1]

                print("---")
                
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