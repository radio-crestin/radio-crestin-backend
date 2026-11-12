"""
Radio Crestin Celery tasks.
"""

# Import focused cleanup tasks
from .delete_stale_listening_sessions import delete_stale_listening_sessions
from .delete_old_anonymous_users import delete_old_anonymous_users
from .delete_old_now_playing_history import delete_old_now_playing_history
from .check_song_thumbnail import check_song_thumbnail
from .send_announcement_push import send_announcement_push, send_scheduled_announcement_pushes
from .delete_old_announcement_events import delete_old_announcement_events
from .trigger_web_deploy import trigger_web_deploy

__all__ = [
    'delete_stale_listening_sessions',
    'delete_old_anonymous_users',
    'delete_old_now_playing_history',
    'check_song_thumbnail',
    'send_announcement_push',
    'send_scheduled_announcement_pushes',
    'delete_old_announcement_events',
    'trigger_web_deploy',
]