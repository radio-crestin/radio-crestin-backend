# Tasks App - Quick Guide

## Creating a New Task

### 1. Task Location
Create tasks in `superapp/apps/<app_name>/tasks/<task_name>.py`

### 2. Basic Task Structure
```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def my_task(param):
    """Task description"""
    try:
        # Task logic here
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

### 3. Task with Retries
```python
@shared_task(bind=True, max_retries=3)
def retry_task(self, param):
    try:
        # Task logic
        return result
    except Exception as e:
        self.retry(countdown=60 * 2**self.request.retries)
```

## Architecture Integration

### Celery Configuration
- **Broker**: Redis (`REDIS_BROKER_URL`)
- **Result Backend**: Django DB
- **Auto-discovery**: Tasks automatically found in any app's `tasks.py` or `tasks/` directory
- **Settings**: Extended in `superapp/apps/tasks/settings.py`

### Task Execution
```python
# Immediate execution
my_task.delay(param)

# Scheduled execution
from datetime import datetime, timedelta
my_task.apply_async(args=[param], eta=datetime.now() + timedelta(hours=1))
```

### Workers
- **priority-worker**: High-priority queue
- **worker**: Default queue
- Started via Docker Compose services

### Admin Integration
- Task results viewable in Django Admin under "Celery Management"
- Periodic tasks manageable via django-celery-beat

## Key Points
- Tasks auto-discovered - no registration needed
- Use `@shared_task` decorator for app-agnostic tasks
- Tasks must be in `tasks.py` or `tasks/` directory
- Always handle exceptions and add logging
- Results stored in database for tracking