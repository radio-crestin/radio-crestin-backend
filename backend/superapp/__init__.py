import sys

# Monkey-patch Django's BaseContext.__copy__ for Python 3.14+ compatibility.
# Django 5.1's BaseContext.__copy__ uses `copy(super())` which fails in Python 3.14
# because super() proxy objects no longer support attribute setting.
if sys.version_info >= (3, 14):
    from django.template.context import BaseContext

    def _basecontext_copy(self):
        duplicate = type(self).__new__(type(self))
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = _basecontext_copy

try:
    from superapp.apps.tasks.celery_entrypoint import celery_app
    __all__ = ('celery_app',)
except ImportError:
    celery_app = None
    __all__ = ()
