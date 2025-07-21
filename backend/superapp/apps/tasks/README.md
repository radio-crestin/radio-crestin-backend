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

## Adding Tasks to Other Apps

### Minimal Setup
To add tasks to any app in the superapp structure:

1. **Create task file**: Add `tasks.py` or `tasks/` directory in your app
2. **Import decorator**: Use `from celery import shared_task`
3. **Define tasks**: Decorate functions with `@shared_task`

### Example Task
```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_data(data_id: int):
    """Process data asynchronously"""
    try:
        # Your processing logic
        result = {"status": "completed", "data_id": data_id}
        logger.info(f"Processed data: {data_id}")
        return result
    except Exception as error:
        logger.error(f"Processing failed: {error}")
        return {"status": "failed", "error": str(error)}

@shared_task(bind=True, max_retries=3)
def retry_task(self, param):
    """Task with retry logic"""
    try:
        # Your logic here
        return {"success": True}
    except Exception as error:
        # Exponential backoff retry
        self.retry(countdown=60 * 2**self.request.retries)
```

### Usage
```python
# Queue task immediately
process_data.delay(123)

# Schedule for later
from datetime import datetime, timedelta
process_data.apply_async(args=[123], eta=datetime.now() + timedelta(minutes=5))
```

### Auto-Discovery
Tasks are automatically discovered by Celery - no additional configuration needed. Just ensure your app is in `INSTALLED_APPS`.
