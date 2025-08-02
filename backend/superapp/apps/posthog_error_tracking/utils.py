import posthog
from os import environ


def track_event(user_id, event_name, properties=None):
    """
    Utility function to track custom events in PostHog
    
    Args:
        user_id: The ID of the user (or 'anonymous' for anonymous users)
        event_name: The name of the event to track
        properties: Optional dictionary of properties to include with the event
    
    Example:
        track_event('user-123', 'station_played', {
            'station_id': 'station-456',
            'station_name': 'Radio Station Name',
            'duration': 300
        })
    """
    if not environ.get('POSTHOG_API_KEY'):
        return
    
    if properties is None:
        properties = {}
    
    try:
        posthog.capture(user_id, event_name, properties)
    except Exception as e:
        pass


def track_user_login(user):
    """
    Track user login event
    """
    if not user or not user.is_authenticated:
        return
        
    properties = {
        'email': getattr(user, 'email', ''),
        'username': getattr(user, 'username', ''),
        '$process_person_profile': True
    }
    
    track_event(str(user.id), 'user_login', properties)


def track_user_signup(user):
    """
    Track user signup event
    """
    if not user:
        return
        
    properties = {
        'email': getattr(user, 'email', ''),
        'username': getattr(user, 'username', ''),
        '$process_person_profile': True
    }
    
    track_event(str(user.id), 'user_signup', properties)


def track_exception(exception, context=None, user_id='anonymous'):
    """
    Track an exception to PostHog using the native capture_exception method
    
    Args:
        exception: The exception object to track
        context: Optional dictionary of additional context about the exception
        user_id: The ID of the user (defaults to 'anonymous')
    
    Example:
        try:
            # some code that might raise an exception
        except Exception as e:
            track_exception(e, {'operation': 'data_processing', 'file': 'data.csv'})
    """
    if not environ.get('POSTHOG_API_KEY'):
        return
    
    # Prepare properties with any additional context
    properties = context or {}
    
    try:
        # Use PostHog's native capture_exception method
        posthog.capture_exception(exception, distinct_id=user_id, properties=properties)
    except Exception as e:
        # Don't let tracking errors break the application
        pass