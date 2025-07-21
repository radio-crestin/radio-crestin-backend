import os
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django_celery_results.models import TaskResult
import redis


def drop_all_tasks():
    url = urlparse(os.environ.get('REDIS_BROKER_URL'))

    # Clear Redis
    redis_client = redis.StrictRedis(
        host=url.hostname,
        port=url.port,
        password=url.password,
        db=int(url.path[1:])
    )
    redis_client.flushall()

    # Clear database
    TaskResult.objects.all().delete()


class Command(BaseCommand):
    help = 'Clear all Celery tasks'

    def handle(self, *args, **kwargs):
        drop_all_tasks()
        self.stdout.write(self.style.SUCCESS('Cleared all tasks'))
