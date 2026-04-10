FROM mirror.gcr.io/library/alpine:3.21

RUN apk add --no-cache bash nginx ffmpeg opus-tools python3 gettext
RUN mkdir -p /data/hls /data/dash /tmp/nginx

COPY scripts/ /app/scripts/
COPY nginx/ /app/nginx/
RUN chmod +x /app/scripts/*.sh

HEALTHCHECK --start-period=30s --interval=15s --timeout=5s --retries=3 \
  CMD /app/scripts/healthcheck.sh

CMD ["/app/scripts/entrypoint.sh"]
