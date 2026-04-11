FROM mirror.gcr.io/library/alpine:3.21

RUN apk add --no-cache bash nginx python3 gettext

# Install ffmpeg with libfdk_aac (HE-AAC/AAC+) support
# homebridge/ffmpeg-for-homebridge includes libfdk_aac built with HE-AAC
RUN echo "Installing ffmpeg for $(uname -m)..." && \
    wget -qO- https://github.com/homebridge/ffmpeg-for-homebridge/releases/download/v2.1.7/ffmpeg-alpine-$(uname -m).tar.gz | tar xzf - -C / --no-same-owner

RUN mkdir -p /data/hls/aac /data/hls/opus /data/cache/playlist /data/cache/s3 /tmp/nginx

COPY scripts/ /app/scripts/
COPY nginx/ /app/nginx/
COPY player.html /app/player.html
RUN chmod +x /app/scripts/*.sh

HEALTHCHECK --start-period=30s --interval=15s --timeout=5s --retries=3 \
  CMD /app/scripts/healthcheck.sh

CMD ["/app/scripts/entrypoint.sh"]
