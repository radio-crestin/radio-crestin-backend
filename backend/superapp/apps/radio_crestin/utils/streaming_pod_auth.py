"""Whether a request comes from a streaming pod: the shared X-Streaming-Api-Key."""
import os
import secrets


def is_streaming_pod(request) -> bool:
    """True only when STREAMING_POD_API_KEY is set and the header matches it
    (compared in constant time). An unset key refuses everyone."""
    expected = os.getenv('STREAMING_POD_API_KEY', '')
    provided = request.headers.get('X-Streaming-Api-Key', '')
    return bool(expected) and secrets.compare_digest(provided.encode(), expected.encode())
