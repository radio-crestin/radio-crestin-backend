FROM alpine:3.19

# Install required packages
RUN apk add --update \
    bash \
    curl \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers

# Install additional codec support
RUN apk add rav1e-libs --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community

# Install ffmpeg optimized for Alpine
RUN curl -Lf# https://github.com/homebridge/ffmpeg-for-homebridge/releases/download/v2.1.1/ffmpeg-alpine-aarch64.tar.gz | tar xzf - -C / --no-same-owner

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create directories
RUN mkdir -p /app/logs /tmp/logs /data

# Copy application files
COPY scripts/ /app/scripts/
COPY nginx/ /app/nginx/

# Set working directory
WORKDIR /app

# Health check for HLS streaming
HEALTHCHECK --start-period=10s --interval=5s --timeout=3s \
  CMD python3 scripts/health_check.py

# Default command
CMD ["python3", "scripts/hls_manager.py"]