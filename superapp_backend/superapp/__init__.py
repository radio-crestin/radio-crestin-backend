try:
    from superapp.apps.tasks.celery_entrypoint import celery_app
    __all__ = ('celery_app',)
except ImportError:
    celery_app = None
    __all__ = ()
