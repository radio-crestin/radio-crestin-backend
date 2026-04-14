# Gunicorn + Uvicorn Configuration

ASGI server setup using Gunicorn as process manager with Uvicorn workers.

## Files

- `gunicorn.py` - Production configuration
- `gunicorn-dev.py` - Development configuration (single worker, auto-reload)
- `run-server.sh` - Server startup script with health monitoring and auto-restart

## How It Works

- **Gunicorn** manages worker processes (spawning, restarting, graceful shutdown)
- **Uvicorn** handles requests via ASGI with `uvloop` (2-4x faster than standard asyncio)
- Each worker handles many concurrent connections asynchronously

## Configuration

### Production (`gunicorn.py`)
- **Workers**: `CPU cores * 2 + 1`
- **Worker Class**: `uvicorn.workers.UvicornWorker`
- **Timeout**: 120s
- **Max Requests**: 1000 (with jitter to prevent thundering herd)
- **Worker Lifetime**: 3600s (recycled to prevent memory leaks)

### Development (`gunicorn-dev.py`)
- **Workers**: 1
- **Worker Class**: `uvicorn.workers.UvicornWorker`
- **Auto-reload**: Enabled
- **Logging**: Debug level

## Usage

```bash
# Production (default)
./scripts/run-server.sh

# Development
DEBUG=true ./scripts/run-server.sh

# Direct
gunicorn --config scripts/gunicorn.py superapp.asgi:application
```

## Auto-Restart Features

The `run-server.sh` script provides:
- Health monitoring via `/health/` endpoint
- Automatic restart on failure (up to 10 attempts)
- Graceful shutdown on SIGTERM/SIGINT

## Dependencies

- `gunicorn>=23.0.0`
- `uvicorn[standard]>=0.34.0` (includes `uvloop` + `httptools`)
