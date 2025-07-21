FROM python:3.11 AS requirements
WORKDIR /app
COPY . /app
RUN ./scripts/generate-requirements.sh > ./unified_requirements.txt

FROM python:3.11

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DOCKER_CONTAINER 1

# Install system dependencies for Gunicorn and performance
RUN apt-get update && apt-get install -y \
    gettext \
    build-essential \
    python3-dev \
    libevent-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel

COPY --from=requirements /app/unified_requirements.txt /app/
# Install all requirements including Gunicorn
RUN pip install -r /app/unified_requirements.txt --no-cache-dir;
RUN pip install psycopg2-binary;

COPY . /app

RUN python manage.py collectstatic --noinput
RUN #python manage.py compilemessages
VOLUME /app/.next/cache
RUN useradd -m -u 1001 -s /bin/bash app && \
    mkdir -p /app/.next/cache && \
    chown -R app:app /app/.next && \
    chmod -R 755 /app/.next
USER 1001

# Install curl for healthcheck
USER root
RUN apt-get update && apt-get install -y curl
USER 1001

EXPOSE 8080
LABEL org.opencontainers.image.source=https://github.com/bringes/easywindows

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8080/health/ || exit 1

CMD ["/app/scripts/run-server.sh"]
