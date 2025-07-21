# Backend HLS Streaming Service

This service provides HLS (HTTP Live Streaming) conversion for radio stations integrated with the radio-crestin backend.

## Architecture

- **Alpine-based Docker container** with FFmpeg support
- **Python process manager** for handling multiple FFmpeg streams
- **NGINX server** for HLS serving with compression and analytics
- **GraphQL integration** with the backend for station management
- **Real-time listener analytics** tracking

## Directory Structure

```
backend_hls_streaming/
├── Dockerfile              # Alpine-based container with FFmpeg and Python
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── hls_manager.py      # Main HLS process manager (task 3)
│   └── health_check.py     # Container health check
├── nginx/
│   └── nginx.conf          # NGINX configuration for HLS serving
├── logs/                   # Log directory (mounted volume)
└── README.md              # This file
```

## Features

### Implemented (Task 2)
- ✅ Alpine Docker base with FFmpeg
- ✅ Python environment with required dependencies  
- ✅ Basic NGINX configuration for HLS serving
- ✅ Health check system
- ✅ Directory structure and documentation

### Pending Implementation
- **Task 3**: HLS Manager Python script with GraphQL integration
- **Task 4**: Enhanced NGINX with anonymous session tracking
- **Task 5**: Log monitoring script for listener analytics
- **Task 10**: Docker-compose integration
- **Task 11**: Auto-restart and metadata handling
- **Task 12**: Log rotation management

## Dependencies

- **ffmpeg-python**: FFmpeg process management
- **requests**: HTTP client for GraphQL communication
- **python-dotenv**: Environment configuration
- **psutil**: Process monitoring and management

## Integration Points

1. **Backend GraphQL**: Fetches stations with `generate_hls_stream: true`
2. **Database**: Writes listener analytics to ListeningSessions model
3. **File System**: Serves HLS files via NGINX with analytics tracking
4. **Monitoring**: Health checks and process management

## Configuration

The service will be configured via environment variables:
- `GRAPHQL_ENDPOINT`: Backend GraphQL endpoint
- `GRAPHQL_TOKEN`: Authentication token
- `LOG_LEVEL`: Logging verbosity
- `STREAM_REFRESH_INTERVAL`: Station list refresh frequency (60s)

## Health Check

The health check monitors:
- Active HLS playlist generation
- Recent file updates (< 60 seconds)
- FFmpeg process health

## Logging

- **Application logs**: Python process management logs
- **FFmpeg logs**: Per-station logs in `/tmp/logs/<station>.log`
- **NGINX logs**: Access logs with session tracking for analytics
- **Log rotation**: 20MB max per station log file