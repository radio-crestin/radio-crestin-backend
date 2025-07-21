# Django SuperApp - Tasks
### Getting Started
1. Setup the project using the instructions from https://django-superapp.bringes.io/
2. Setup `tasks` app using the below instructions:
```bash
cd my_superapp;
cd superapp/apps;
django_superapp bootstrap-app \
    --template-repo https://github.com/django-superapp/django-superapp-tasks ./tasks;
cd ../../;
```

## Docker Compose Configuration

To enable Celery workers for task processing, add the following services to your `docker-compose.yml`:

### Priority Worker Service
```yaml
priority-worker:
  build:
    context: .
    dockerfile: Dockerfile
  restart: unless-stopped
  depends_on:
    - "postgres"
    - "redis"
  volumes:
    - .:/app:delegated
    - /app/__pycache__
    - /app/**/__pycache__
  env_file:
    - .env
  command: ./scripts/run-priority-worker.sh
  healthcheck:
    test: ["CMD", "ps", "aux", "|", "grep", "[c]elery -A superapp worker"]
    interval: 30s
    timeout: 10s
    retries: 3
  logging:
    driver: "json-file"
    options:
      max-file: "5"
      max-size: "100m"
```

### Worker Service
```yaml
worker:
  build:
    context: .
    dockerfile: Dockerfile
  restart: unless-stopped
  depends_on:
    - "postgres"
    - "redis"
  volumes:
    - .:/app:delegated
    - /app/__pycache__
    - /app/**/__pycache__
  env_file:
    - .env
  command: ./scripts/run-worker.sh
  healthcheck:
    test: ["CMD", "ps", "aux", "|", "grep", "[c]elery -A superapp worker"]
    interval: 30s
    timeout: 10s
    retries: 3
  logging:
    driver: "json-file"
    options:
      max-file: "5"
      max-size: "100m"
```

These services provide:
- **priority-worker**: Handles high-priority tasks
- **worker**: Handles regular tasks
- Both services include health checks and proper logging configuration
- Dependencies on postgres and redis are properly configured
