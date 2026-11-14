"""
Gunicorn production configuration: WSGI with threaded (gthread) workers.

Every view is synchronous, so ASGI only added cost: Django ran each request
on a thread of its own, which opened a new database connection (a TLS
handshake to PgBouncer, ~18 ms CPU in prod) on every request that touched
the database. A gthread worker keeps its threads, so each thread keeps its
connection for CONN_MAX_AGE.
"""
import multiprocessing
import logging
import os

# Server
bind = "0.0.0.0:8080"
backlog = 2048

# Workers — capped at 2 to keep memory under control in containerized environments
# Each worker loads ~200MB (Django + boto3 + strawberry + graphql-core).
workers = min(int(os.environ.get("GUNICORN_WORKERS", 2)), 4)
worker_class = "gthread"
# Requests in flight per worker; each thread holds one database connection.
threads = int(os.environ.get("GUNICORN_THREADS", 16))
# A worker boot costs about 3 s of CPU in prod. At 1000 requests a worker
# restarted every 4-5 minutes (~50 boots an hour); this still recycles each
# worker about hourly.
max_requests = 20000
max_requests_jitter = 2000
timeout = 120
keepalive = 5
graceful_timeout = 30
max_worker_lifetime = 3600

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
# %(D)s: request duration in microseconds. X-Forwarded-For names the client
# behind the ingress (%(h)s is the ingress). %({host}i)s: the Host header,
# which ALLOWED_HOSTS must cover.
access_log_format = '%(h)s %({x-forwarded-for}i)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %({host}i)s %(D)s'


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
# Gunicorn 24+ opens a control socket under $HOME; nothing uses it.
control_socket_disable = True
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
    server.log.info("Gunicorn ready on %s", server.address)


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
