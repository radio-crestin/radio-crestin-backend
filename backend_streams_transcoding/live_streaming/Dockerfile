FROM mirror.gcr.io/library/alpine:3.21

RUN apk add --no-cache bash nginx nginx-mod-http-brotli nginx-mod-http-zstd python3 py3-pip gettext

# Install ffmpeg with libfdk_aac for high-quality AAC-LC encoding.
# AAC-LC (mp4a.40.2) is the only profile guaranteed across every iOS / Android
# version per Apple HLS Authoring Spec, and avoids SBR boundary artifacts.
RUN echo "Installing ffmpeg for $(uname -m)..." && \
    wget -qO- https://github.com/homebridge/ffmpeg-for-homebridge/releases/download/v2.1.7/ffmpeg-alpine-$(uname -m).tar.gz | tar xzf - -C / --no-same-owner

# Install Python dependencies for the scraper engine + posthog reporting.
# Using --break-system-packages since this is a container.
RUN pip3 install --no-cache-dir --break-system-packages \
    posthog==7.10.3

RUN mkdir -p /data/hls/aac /data/cache/playlist /data/cache/s3 /tmp/nginx

COPY scripts/ /app/scripts/
COPY nginx/ /app/nginx/
COPY player.html /app/player.html
COPY master.m3u8 /app/master.m3u8
RUN chmod +x /app/scripts/*.sh

HEALTHCHECK --start-period=30s --interval=15s --timeout=5s --retries=3 \
  CMD /app/scripts/healthcheck.sh

CMD ["/app/scripts/entrypoint.sh"]
