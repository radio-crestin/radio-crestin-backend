"""
Custom Gunicorn worker that handles connection aborts gracefully
"""

import sys
import logging
from gunicorn.workers.sync import SyncWorker

logger = logging.getLogger(__name__)


class QuietSyncWorker(SyncWorker):
    """
    Custom sync worker that suppresses connection abort errors
    
    This worker catches SystemExit and other connection errors that occur
    when clients disconnect before sending complete requests.
    """
    
    def handle(self, listener, client, addr):
        """
        Override handle to catch and suppress connection abort errors
        """
        try:
            super().handle(listener, client, addr)
        except SystemExit as e:
            # Client disconnected - this is normal, don't log as error
            if e.code == 1:
                logger.debug(f"Client disconnected from {addr}")
            else:
                raise
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Connection issues - log at debug level only
            logger.debug(f"Connection error from {addr}")
        except Exception as e:
            # For other exceptions, check if it's a known connection issue
            error_msg = str(e).lower()
            if any(x in error_msg for x in ['broken pipe', 'connection reset', 'connection aborted', 'no uri read']):
                logger.debug(f"Connection issue from {addr}: {e}")
            else:
                # Re-raise unknown errors
                logger.error(f"Unexpected error handling request from {addr}: {e}")
                raise
    
    def handle_request(self, listener, req, client, addr):
        """
        Override to add additional error handling for request processing
        """
        try:
            # Skip logging for health check endpoints
            if req and hasattr(req, 'path'):
                if req.path in ['/health', '/ready', '/healthz', '/readyz']:
                    # Process health checks quietly
                    return super().handle_request(listener, req, client, addr)
            
            return super().handle_request(listener, req, client, addr)
        except SystemExit:
            # Suppress SystemExit from connection aborts
            logger.debug(f"Request aborted from {addr}")
            return False
        except Exception as e:
            # Log other errors at appropriate level
            error_msg = str(e).lower()
            if 'no uri read' in error_msg:
                logger.debug(f"No URI read from {addr}")
                return False
            else:
                logger.error(f"Error processing request from {addr}: {e}")
                raise