FROM alpine:3.19

# Install required packages including NGINX
RUN apk add --update \
    bash \
    curl \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers \
    nginx \
    nginx-mod-http-brotli

# Install additional codec support
RUN apk add rav1e-libs --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community

# Install ffmpeg based on architecture
RUN echo "Installing ffmpeg for $(uname -m)..." && \
    curl -Lf# https://github.com/homebridge/ffmpeg-for-homebridge/releases/download/v2.1.7/ffmpeg-alpine-$(uname -m).tar.gz | tar xzf - -C / --no-same-owner

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

# Create directories
RUN mkdir -p /app/logs /tmp/logs /data /tmp/client_temp

# Copy application files
COPY scripts /app/scripts/
COPY nginx /app/nginx/

# Set working directory
WORKDIR /app

# Health check for HLS streaming
HEALTHCHECK --start-period=10s --interval=5s --timeout=3s \
  CMD python3 scripts/health_check.py

# Make scripts executable
RUN chmod +x /app/scripts/*.py

# Default command - run both HLS Manager and Log Monitor via supervisor
CMD ["python3", "scripts/supervisor.py"]
