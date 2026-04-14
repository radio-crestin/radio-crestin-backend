"""
Gunicorn production configuration with Uvicorn ASGI workers.

Gunicorn manages worker processes (spawning, restarts, signals).
Uvicorn handles requests via ASGI with uvloop for high concurrency.
"""
import multiprocessing
import logging
import os

# Server
bind = "0.0.0.0:8080"
backlog = 2048

# Workers — capped at 2 to keep memory under control in containerized environments
# Each worker loads ~200MB (Django + boto3 + strawberry + graphql-core).
# Uvicorn workers handle concurrency via async, so 2 workers is sufficient.
workers = min(int(os.environ.get("GUNICORN_WORKERS", 2)), 4)
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5
graceful_timeout = 30
max_worker_lifetime = 3600

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'


class ConnectionErrorFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return "no URI read" not in msg and "SystemExit: 1" not in msg


logging.getLogger("gunicorn.error").addFilter(ConnectionErrorFilter())

# Security
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Process
proc_name = "gunicorn_superapp"
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = 1001
group = 1001
worker_tmp_dir = "/tmp"

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=superapp.settings',
]


def when_ready(server):
    server.log.info("Gunicorn + Uvicorn ready on %s", server.address)


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
