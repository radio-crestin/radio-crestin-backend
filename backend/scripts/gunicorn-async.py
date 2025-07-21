"""
Gunicorn configuration for async workloads using gevent
Use this configuration when you need to handle many concurrent I/O-bound requests
"""
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes - fewer workers for async
workers = multiprocessing.cpu_count() + 1
worker_class = "gevent"
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

# Process naming
proc_name = "gunicorn_superapp_async"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn-async.pid"
user = 1001
group = 1001
tmp_upload_dir = None
umask = 0

# Worker process management
worker_tmp_dir = "/dev/shm"
enable_stdio_inheritance = True

# Application
wsgi_module = "superapp.wsgi:application"

# Restart settings
graceful_timeout = 30
shutdown_timeout = 30

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=superapp.settings',
]

# Async-specific settings
async_timeout = 30
async_pool_size = 100

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn async server with gevent...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn async server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn async server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Async worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Async worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Async worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Async worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Async worker received SIGABRT signal")
