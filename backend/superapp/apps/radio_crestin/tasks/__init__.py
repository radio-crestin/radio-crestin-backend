"""
Radio Crestin Celery tasks.
"""

# Import all tasks from individual modules
from .cleanup_old_sessions import cleanup_old_listening_sessions
from .cleanup_old_users import cleanup_old_app_users
from .cleanup_stale_sessions import (
    delete_inactive_listening_sessions,
    mark_stale_sessions_inactive_and_delete
)
from .nightly_cleanup import nightly_database_cleanup

__all__ = [
    'cleanup_old_listening_sessions',
    'cleanup_old_app_users',
    'delete_inactive_listening_sessions',
    'mark_stale_sessions_inactive_and_delete',
    'nightly_database_cleanup',
]