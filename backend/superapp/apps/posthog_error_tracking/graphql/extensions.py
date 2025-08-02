import json
import logging
import time
import traceback
from typing import Any, Dict, Optional

from strawberry.extensions import SchemaExtension
from graphql import GraphQLError

from superapp.apps.posthog_error_tracking.utils import track_exception

logger = logging.getLogger(__name__)


class PostHogErrorTrackingExtension(SchemaExtension):
    """
    GraphQL extension to track parsing, validation, execution errors and exceptions to PostHog.
    
    This extension hooks into different phases of GraphQL query processing:
    - on_parse: Tracks parsing errors
    - on_validate: Tracks validation errors
    - on_execute: Tracks execution errors and exceptions
    """
    
    def __init__(self):
        super().__init__()
        self.start_time = None
        self.phase_times = {}
    
    def _get_request_info(self) -> Dict[str, Any]:
        """Extract request information from the execution context"""
        try:
            context = self.execution_context.context
            request = context.get('request') if hasattr(context, 'get') else getattr(context, 'request', None)
            
            if request:
                # Extract query information
                query = self.execution_context.query or ''
                variables = self.execution_context.variables or {}
                operation_name = self.execution_context.operation_name or ''
                
                return {
                    'graphql_query': query[:500],  # Limit query length
                    'graphql_variables': json.dumps(variables) if variables else '{}',
                    'graphql_operation_name': operation_name,
                    'path': getattr(request, 'path', ''),
                    'method': getattr(request, 'method', ''),
                }
            
            return {
                'graphql_query': self.execution_context.query[:500] if self.execution_context.query else '',
                'graphql_variables': json.dumps(self.execution_context.variables) if self.execution_context.variables else '{}',
                'graphql_operation_name': self.execution_context.operation_name or '',
            }
        except Exception:
            return {}
    
    def _get_user_id(self) -> str:
        """Get user ID from the request context"""
        try:
            context = self.execution_context.context
            request = context.get('request') if hasattr(context, 'get') else getattr(context, 'request', None)
            
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                return str(request.user.id)
        except Exception:
            pass
        
        return 'anonymous'
    
    def _track_graphql_exception(self, exception: Exception, phase: str):
        """Generic function to track GraphQL exceptions to PostHog"""
        try:
            # Get request information
            request_info = self._get_request_info()
            
            # Build error context
            error_context = {
                **request_info,
                'error_message': str(exception),
                'error_type': type(exception).__name__,
                'error_category': f'graphql_{phase}_exception',
                'phase': phase,
                'execution_time_ms': self.phase_times.get(phase, 0),
            }
            
            # Add GraphQL-specific error details if available
            if isinstance(exception, GraphQLError):
                error_context.update({
                    'graphql_error_message': exception.message,
                    'graphql_error_path': str(exception.path) if exception.path else None,
                    'graphql_error_locations': str(exception.locations) if exception.locations else None,
                })
            
            # Get traceback
            tb = traceback.format_exc()
            error_context['traceback'] = tb
            
            # Get user ID
            user_id = self._get_user_id()
            
            # Track the exception
            track_exception(exception, error_context, user_id)
            
            # Don't track as separate event - just use track_exception
            
            # Log for debugging
            logger.error(f"GraphQL {phase} exception: {exception}")
            logger.debug(f"Exception traceback:\n{tb}")
            
        except Exception as tracking_error:
            logger.error(f"Failed to track {phase} exception to PostHog: {tracking_error}")
    
    def on_operation_start(self):
        """Called when the operation starts"""
        self.start_time = time.time()
    
    def on_parse(self):
        """Track parsing errors"""
        parse_start = time.time()
        
        try:
            yield
        except Exception as e:
            # Calculate parse time
            self.phase_times['parse'] = int((time.time() - parse_start) * 1000)
            
            # Track the parsing exception
            self._track_graphql_exception(e, 'parse')
            
            # Re-raise the exception
            raise
        else:
            # Calculate parse time for successful parsing
            self.phase_times['parse'] = int((time.time() - parse_start) * 1000)
    
    def on_validate(self):
        """Track validation errors"""
        validate_start = time.time()
        
        try:
            yield
        except Exception as e:
            # Calculate validation time
            self.phase_times['validate'] = int((time.time() - validate_start) * 1000)
            
            # Track the validation exception
            self._track_graphql_exception(e, 'validate')
            
            # Re-raise the exception
            raise
        else:
            # Calculate validation time for successful validation
            self.phase_times['validate'] = int((time.time() - validate_start) * 1000)
    
    def on_execute(self):
        """Track execution errors and exceptions"""
        execute_start = time.time()
        
        try:
            result = yield
            
            # Calculate execution time
            self.phase_times['execute'] = int((time.time() - execute_start) * 1000)
            
            # Check if the result contains errors
            if hasattr(result, 'errors') and result.errors:
                for error in result.errors:
                    # Track each GraphQL error
                    self._track_graphql_exception(error, 'execute')
            
            return result
            
        except Exception as e:
            # Calculate execution time
            self.phase_times['execute'] = int((time.time() - execute_start) * 1000)
            
            # Track the execution exception
            self._track_graphql_exception(e, 'execute')
            
            # Re-raise the exception
            raise
    
    def on_operation_end(self):
        """Called when the operation ends"""
        # We only track errors/exceptions, not successful operations
        pass


__all__ = ["PostHogErrorTrackingExtension"]
