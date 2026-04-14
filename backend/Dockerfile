FROM mirror.gcr.io/library/python:3.14 AS requirements
WORKDIR /app
# Copy everything but only to extract requirements — this stage is cheap
COPY . /app
# Collect all requirements.txt files into one
RUN cat requirements.txt > unified_requirements.txt && echo "" >> unified_requirements.txt && \
    find /app/superapp -name "requirements.txt" -exec sh -c 'cat "$1"; echo ""' _ {} \; >> unified_requirements.txt

FROM mirror.gcr.io/library/python:3.14

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER_CONTAINER=1

# Install system dependencies (curl included here, not in a separate layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    build-essential \
    python3-dev \
    libevent-dev \
    libffi-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached unless requirements change)
COPY --from=requirements /app/unified_requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/unified_requirements.txt psycopg2-binary

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
