"""
Quiet Gunicorn configuration that suppresses connection abort errors

This is a simpler configuration focused on reducing noise from connection issues.
"""

import os
import multiprocessing
import logging
import sys

# Patch logging before Gunicorn starts
class QuietErrorFilter(logging.Filter):
    """Filter out noisy connection errors"""
    
    SUPPRESSED_MESSAGES = [
        'no URI read',
        'SystemExit: 1',
        'handle_abort',
        'Connection reset by peer',
        'Broken pipe',
    ]
    
    def filter(self, record):
        msg = str(record.getMessage())
        # Check if this is a message we want to suppress
        for suppressed in self.SUPPRESSED_MESSAGES:
            if suppressed in msg:
                return False
        return True

# Configure logging early
logging.basicConfig(level=logging.INFO)
error_logger = logging.getLogger('gunicorn.error')
error_logger.addFilter(QuietErrorFilter())

# Import base configuration
from gunicorn import *

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

# Worker class
worker_class = "sync"
threads = 2

# Logging - quieter settings
accesslog = "-"
errorlog = "-"
loglevel = "warning"  # Higher level to reduce noise
capture_output = True  # Capture stdout/stderr to prevent spam
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s "%(a)s" %(D)s'

# Process naming
proc_name = "gunicorn_superapp"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = 1001
group = 1001
worker_tmp_dir = "/tmp"

# Application
wsgi_module = "superapp.wsgi:application"

# Restart settings
graceful_timeout = 30

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=superapp.settings',
    'PYTHONUNBUFFERED=1',
]

def when_ready(server):
    """Called when server is ready"""
    server.log.info("Gunicorn server ready on %s", server.address)

def pre_request(worker, req):
    """Called before processing a request"""
    # Don't log health checks
    if hasattr(req, 'path') and req.path in ['/health', '/ready', '/healthz']:
        return
    worker.log.debug("%s %s", req.method, req.path)

def post_request(worker, req, environ, resp):
    """Called after processing a request"""
    # Don't log health checks
    if hasattr(req, 'path') and req.path in ['/health', '/ready', '/healthz']:
        return
    # Only log errors
    if hasattr(resp, 'status_code') and resp.status_code >= 400:
        worker.log.info("%s %s %s", req.method, req.path, resp.status_code)