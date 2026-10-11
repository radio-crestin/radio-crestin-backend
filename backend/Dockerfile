FROM mirror.gcr.io/library/python:3.14 AS requirements
WORKDIR /app
# Copy everything but only to extract requirements — this stage is cheap
COPY . /app
# Collect all requirements.txt files into one
RUN cat requirements.txt > unified_requirements.txt && echo "" >> unified_requirements.txt && \
    find /app/superapp -name "requirements.txt" -exec sh -c 'cat "$1"; echo ""' _ {} \; >> unified_requirements.txt

# Build stage: the full image has compilers, headers and git for any package
# that builds from source. None of it ships: only the venv is copied out.
FROM mirror.gcr.io/library/python:3.14 AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (cached unless requirements change)
# constraints.txt pins every package to the versions production runs, so a
# rebuild ships only code changes, never a surprise library upgrade.
COPY --from=requirements /app/unified_requirements.txt /app/
COPY constraints.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/unified_requirements.txt -c /app/constraints.txt psycopg2-binary

# Static ffmpeg/ffprobe (the stream_id3 scraper runs ffprobe). Debian's
# ffmpeg package drags in libxml2, openexr and others with unfixed critical CVEs.
FROM mirror.gcr.io/mwader/static-ffmpeg:8.1.2@sha256:33f770f812cbfc3de96c547157fc9faf8bd95a36481753439ffa761045167585 AS ffmpeg

# Runtime stage: slim image with no compilers or -dev packages
FROM mirror.gcr.io/library/python:3.14-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER_CONTAINER=1
ENV PATH="/opt/venv/bin:$PATH"

# curl: run-server.sh and the HEALTHCHECK probe /health/ with it
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
COPY --from=builder /opt/venv /opt/venv

# Create non-root user before copying source
RUN useradd -m -u 1001 -s /bin/bash app

# Copy source code (this layer rebuilds on any code change, but is fast — just a file copy)
COPY --chown=app:app . /app

RUN python manage.py collectstatic --noinput

USER 1001

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8080/health/ || exit 1

CMD ["/app/scripts/run-server.sh"]
