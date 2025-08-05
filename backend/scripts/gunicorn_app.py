"""
Custom Gunicorn application with enhanced error handling
"""

import sys
import logging
from gunicorn.app.wsgiapp import WSGIApplication
from gunicorn.workers.sync import SyncWorker

logger = logging.getLogger(__name__)


class QuietGunicornApp(WSGIApplication):
    """
    Custom Gunicorn application that suppresses connection errors
    """
    
    def init(self, parser, opts, args):
        """Initialize with custom configuration"""
        super().init(parser, opts, args)
        
        # Override worker class if not specified
        if not opts.worker_class:
            self.cfg.set('worker_class', 'scripts.custom_worker.QuietSyncWorker')
    
    def load_config(self):
        """Load configuration with custom error handling"""
        super().load_config()
        
        # Set up custom logging filters
        self._setup_logging_filters()
    
    def _setup_logging_filters(self):
        """Configure logging to suppress connection errors"""
        class ConnectionErrorFilter(logging.Filter):
            def filter(self, record):
                msg = record.getMessage()
                # Suppress specific connection errors
                if any(x in msg for x in ['no URI read', 'SystemExit: 1', 'handle_abort']):
                    return False
                return True
        
        # Apply to Gunicorn error logger
        error_logger = logging.getLogger('gunicorn.error')
        error_logger.addFilter(ConnectionErrorFilter())
        
        # Also apply to root logger for worker processes
        root_logger = logging.getLogger()
        root_logger.addFilter(ConnectionErrorFilter())


def run():
    """Run the custom Gunicorn application"""
    app = QuietGunicornApp("%(prog)s [OPTIONS] [APP_MODULE]")
    return app.run()


if __name__ == '__main__':
    sys.exit(run())