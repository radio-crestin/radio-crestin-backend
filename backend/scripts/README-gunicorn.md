# Gunicorn Configuration Guide

This directory contains Gunicorn configurations for the EasyWindows Django application.

## Files

- `gunicorn.py` - Production configuration (sync workers)
- `gunicorn-dev.py` - Development configuration (single worker)
- `gunicorn-async.py` - Async configuration (gevent workers for I/O-bound workloads)
- `run-server.sh` - Server startup script with auto-restart functionality
- `test-gunicorn.py` - Configuration validation script

## Configuration Overview

### Production (`gunicorn.py`)
- **Workers**: Auto-calculated based on CPU cores (2 * cores + 1)
- **Worker Class**: `sync` (suitable for CPU-bound Django apps)
- **Threads**: 2 per worker
- **Timeout**: 120 seconds
- **Max Requests**: 1000 (with jitter to prevent thundering herd)
- **Logging**: Info level with structured format
- **Process Management**: Preload app, graceful restarts

### Development (`gunicorn-dev.py`)
- **Workers**: 1 (easier debugging)
- **Worker Class**: `sync`
- **Timeout**: 60 seconds
- **Max Requests**: 500
- **Logging**: Debug level for verbose output
- **Auto-reload**: Enabled for code changes
- **Process Management**: No preloading for faster restarts

### Async (`gunicorn-async.py`)
- **Workers**: CPU cores + 1 (fewer workers for async)
- **Worker Class**: `gevent` (for I/O-bound tasks)
- **Connections**: 1000 per worker
- **Timeout**: 120 seconds
- **Max Requests**: 1000
- **Use Case**: High concurrency I/O-bound workloads

## Usage

### Running Directly
```bash
# Production
gunicorn --config scripts/gunicorn.py superapp.wsgi:application

# Development  
gunicorn --config scripts/gunicorn-dev.py superapp.wsgi:application

# Async (for I/O-bound workloads)
gunicorn --config scripts/gunicorn-async.py superapp.wsgi:application
```

### Using the Run Script
```bash
# Production (DEBUG=false)
./scripts/run-server.sh

# Development (DEBUG=true)
DEBUG=true ./scripts/run-server.sh
```

## Auto-Restart Features

The `run-server.sh` script provides:

- **Health Monitoring**: Periodic checks via `/health/` endpoint
- **Automatic Restart**: Restarts failed processes up to 10 times
- **Graceful Shutdown**: Proper signal handling (SIGTERM/SIGINT)
- **Process Monitoring**: Tracks Gunicorn PID and status
- **Logging**: Timestamped logs for debugging

## Performance Tuning

### Production Optimizations
- Workers auto-scaled based on CPU cores
- Connection pooling with keepalive
- Request limits to prevent memory leaks
- Graceful worker recycling
- Structured logging for monitoring

### Development Optimizations
- Single worker for easier debugging
- Auto-reload on code changes
- Verbose logging for development
- Shorter timeouts for faster feedback

## Monitoring

### Health Check
```bash
curl -f http://localhost:8080/health/
```

### Process Status
```bash
ps aux | grep gunicorn
```

### Logs
Logs are output to stdout/stderr and can be captured by Docker or systemd.

## Troubleshooting

### Common Issues
1. **Port already in use**: Change the `bind` address in config
2. **Workers not starting**: Check Django settings and imports
3. **Memory issues**: Reduce worker count or enable worker recycling
4. **Timeout errors**: Increase `timeout` value in config

### Debug Mode
Set `DEBUG=true` to use development configuration with:
- More verbose logging
- Single worker for easier debugging
- Auto-reload enabled
- Shorter timeouts

## Dependencies

Required packages:
- `gunicorn>=23.0.0`
- `gevent>=24.12.0` (for async worker class if needed)

## Migration from uWSGI

Key differences from uWSGI:
- Simpler configuration format (Python vs INI)
- Better signal handling
- More predictable worker management
- Easier debugging and monitoring
- Built-in health check support