# Gunicorn Configuration

WSGI server setup: Gunicorn with threaded (`gthread`) workers. Every view is
synchronous; under ASGI (Uvicorn workers, used until 2026-11) Django ran each
request on a new thread, which opened a new database connection per request.

## Files

- `gunicorn.py` - Production configuration
- `gunicorn-dev.py` - Development configuration (single worker, auto-reload)
- `run-server.sh` - Server startup script with health monitoring and auto-restart

## How It Works

- **Gunicorn** manages worker processes (spawning, restarting, graceful shutdown)
- Each worker serves `threads` requests at once; each thread keeps its own
  database connection open for `CONN_MAX_AGE`

## Configuration

### Production (`gunicorn.py`)
- **Workers**: `GUNICORN_WORKERS` (default 2, at most 4)
- **Worker Class**: `gthread`, `GUNICORN_THREADS` threads (default 16)
- **Timeout**: 120s
- **Max Requests**: 20000 (with jitter to prevent thundering herd)

### Development (`gunicorn-dev.py`)
- **Workers**: 1
- **Worker Class**: `gthread`, 4 threads
- **Auto-reload**: Enabled
- **Logging**: Debug level

## Usage

```bash
# Production (default)
./scripts/run-server.sh

# Development
DEBUG=true ./scripts/run-server.sh

# Direct
gunicorn --config scripts/gunicorn.py superapp.wsgi:application
```

## Auto-Restart Features

The `run-server.sh` script provides:
- Health monitoring via `/health/` endpoint
- Automatic restart on failure (up to 10 attempts)
- Graceful shutdown on SIGTERM/SIGINT

## Dependencies

- `gunicorn==27.0.*` (its gthread worker finishes the connections it accepted
  when it restarts; 23.0 dropped them)
