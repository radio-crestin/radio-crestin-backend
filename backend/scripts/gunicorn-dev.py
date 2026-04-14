"""
Gunicorn development configuration with Uvicorn ASGI workers.

Single worker with auto-reload for local development.
"""

# Server
bind = "0.0.0.0:8080"

# Workers - single worker for development
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 2
graceful_timeout = 10
max_worker_lifetime = 1800

# Auto-reload on code changes
reload = True

# Logging - verbose for development
accesslog = "-"
errorlog = "-"
loglevel = "debug"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process
proc_name = "gunicorn_superapp_dev"
daemon = False
pidfile = "/tmp/gunicorn-dev.pid"
user = 1001
group = 1001
worker_tmp_dir = "/tmp"

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=superapp.settings',
]


def when_ready(server):
    server.log.info("Dev server ready on %s", server.address)


def post_fork(server, worker):
    server.log.info("Dev worker spawned (pid: %s)", worker.pid)
