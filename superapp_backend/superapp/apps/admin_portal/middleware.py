from threading import local

# Thread-local storage for request-scoped caching
_request_thread_locals = local()


class RequestCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize new cache for this request
        _request_thread_locals.cache = {}
        response = self.get_response(request)
        _request_thread_locals.cache = None

        return response


def set_request_cache(key, value):
    _request_thread_locals.cache[key] = value


def get_request_cache(key):
    return _request_thread_locals.cache.get(key, None)


def get_request_cache_or_create(key, value, ignore_uninitialized=False):
    if ignore_uninitialized and not hasattr(_request_thread_locals, 'cache'):
        return value
    cache_value = get_request_cache(key)
    if not cache_value:
        set_request_cache(key, value)
        return value
    return cache_value
