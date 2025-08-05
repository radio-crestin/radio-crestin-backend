"""
Gunicorn configuration for production environment
"""
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 120
keepalive = 2

# Restart workers after this many seconds to prevent memory leaks
max_worker_lifetime = 3600

# Security
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Suppress connection abort errors
import logging
logging.getLogger("gunicorn.error").setLevel(logging.WARNING)

# Custom error filter to suppress specific errors
class ConnectionErrorFilter(logging.Filter):
    """Filter out connection-related errors"""
    def filter(self, record):
        # Filter out "no URI read" errors
        if "no URI read" in record.getMessage():
            return False
        # Filter out SystemExit from connection aborts
        if "SystemExit: 1" in record.getMessage():
            return False
        return True

# Apply filter to Gunicorn error logger
gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_error_logger.addFilter(ConnectionErrorFilter())

# Process naming
proc_name = "gunicorn_superapp"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = 1001
group = 1001
tmp_upload_dir = None
umask = 0

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Worker process management
worker_tmp_dir = "/tmp"
enable_stdio_inheritance = True

# Application
wsgi_module = "superapp.wsgi:application"

# Restart settings
graceful_timeout = 30
shutdown_timeout = 30

# Performance tuning
worker_class = "sync"  # Use standard sync worker
threads = 2

# Monkey-patch the sync worker to handle connection aborts quietly
def patch_worker():
    """Patch Gunicorn worker to suppress connection errors"""
    try:
        from gunicorn.workers.sync import SyncWorker
        original_handle = SyncWorker.handle
        
        def quiet_handle(self, listener, client, addr):
            try:
                return original_handle(self, listener, client, addr)
            except SystemExit as e:
                if e.code == 1:
                    # Connection abort - suppress silently
                    pass
                else:
                    raise
            except Exception as e:
                if "no URI read" in str(e):
                    # Known connection issue - suppress
                    pass
                else:
                    raise
        
        SyncWorker.handle = quiet_handle
    except ImportError:
        pass  # Gunicorn not available in this context

# Apply the patch when workers are forked
def post_fork(server, worker):
    """Called just after a worker has been forked."""
    patch_worker()
    server.log.info("Worker spawned (pid: %s)", worker.pid)

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=superapp.settings',
]

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawning (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    # Skip logging for health check endpoints to reduce noise
    if req.path in ['/health', '/ready']:
        req.skip_logging = True
    worker.log.debug("%s %s", req.method, req.path)

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    # Skip logging for health checks
    if hasattr(req, 'skip_logging') and req.skip_logging:
        return
    # Log successful requests at debug level
    if resp.status_code < 400:
        worker.log.debug("%s %s %s", req.method, req.path, resp.status_code)
