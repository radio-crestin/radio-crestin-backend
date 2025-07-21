"""
Gunicorn configuration for development environment
"""
import os

# Server socket
bind = "0.0.0.0:8080"
backlog = 64

# Worker processes - minimal for development
workers = 1
worker_class = "sync"
worker_connections = 100
max_requests = 500
max_requests_jitter = 50
preload_app = False  # Disable preloading for easier debugging
timeout = 60
keepalive = 2

# Development-specific settings
reload = True
reload_extra_files = [
    "/app/superapp/",
    "/app/requirements.txt",
    "/app/manage.py",
]

# Logging - more verbose for development
accesslog = "-"
errorlog = "-"
loglevel = "debug"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "gunicorn_superapp_dev"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn-dev.pid"
user = 1001
group = 1001
tmp_upload_dir = None
umask = 0

# Development performance settings
worker_tmp_dir = "/tmp"
enable_stdio_inheritance = True

# Application
wsgi_module = "superapp.wsgi:application"

# Restart settings - more aggressive for development
graceful_timeout = 10
shutdown_timeout = 10
max_worker_lifetime = 1800  # 30 minutes

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=superapp.settings',
]

# Development hooks with more logging
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn development server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn development server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn development server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Development worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Development worker spawning (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Development worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Development worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Development worker received SIGABRT signal")

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info("Number of workers changed from %s to %s", old_value, new_value)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")
