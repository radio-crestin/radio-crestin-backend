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
            for error in self.execution_context.errors:
                print(f"GraphQL Error: {error}")
                print(f"Error Type: {type(error).__name__}")

                # Try to print exception traceback if available
                if hasattr(error, '__cause__') and error.__cause__:
                    print("Exception traceback:")
                    traceback.print_exception(type(error.__cause__), error.__cause__, error.__cause__.__traceback__)
                elif hasattr(error, 'original_error') and error.original_error:
                    print("Exception traceback:")
                    traceback.print_exception(type(error.original_error), error.original_error, error.original_error.__traceback__)
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

                print("---")