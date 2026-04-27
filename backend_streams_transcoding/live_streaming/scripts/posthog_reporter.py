"""
Thin PostHog wrapper for the streamer pod — reports errors and notable events
to the central PostHog project so per-station issues are observable in one
place alongside backend events.

Initialized lazily from POSTHOG_API_KEY. If that's unset (or the posthog
package is missing), every call is a silent no-op so local dev / unconfigured
environments keep working.

Every event auto-tags station_slug, pod_name, and image_tag so PostHog
filters can scope by station or by deployment.
"""

import os
import socket
import sys
import threading
import traceback

_lock = threading.Lock()
_initialized = False
_enabled = False
_default_props: dict = {}
_posthog = None


def _init():
    global _initialized, _enabled, _default_props, _posthog
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        _initialized = True
        api_key = os.environ.get("POSTHOG_API_KEY", "").strip()
        if not api_key:
            return
        try:
            import posthog as _ph
        except ImportError:
            print("posthog_reporter: posthog package not installed; reporting disabled", flush=True)
            return
        _ph.api_key = api_key
        _ph.host = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com").strip()
        _default_props = {
            "station_slug": os.environ.get("STATION_SLUG", "unknown"),
            "pod_name": socket.gethostname(),
            "image_tag": os.environ.get("IMAGES_TAG") or os.environ.get("IMAGE_TAG", ""),
            "service": "live-streaming",
        }
        _posthog = _ph
        _enabled = True
        print(
            f"posthog_reporter: enabled "
            f"(host={_ph.host}, station={_default_props['station_slug']})",
            flush=True,
        )


def _distinct_id() -> str:
    return os.environ.get("STATION_SLUG", "unknown")


def capture_event(event: str, properties: dict | None = None) -> None:
    """Record a custom event. Safe no-op if PostHog isn't configured."""
    _init()
    if not _enabled:
        return
    try:
        props = dict(_default_props)
        if properties:
            props.update(properties)
        _posthog.capture(distinct_id=_distinct_id(), event=event, properties=props)
    except Exception as e:
        print(f"posthog_reporter: capture_event({event}) failed: {e}", flush=True)


def capture_exception(exc: BaseException | None = None, context: dict | None = None) -> None:
    """Record an exception. If exc is None, captures the currently-handled one."""
    _init()
    if not _enabled:
        return
    try:
        if exc is None:
            _t, exc_val, _tb = sys.exc_info()
            if exc_val is None:
                return
            exc = exc_val
        props = dict(_default_props)
        props["error_type"] = type(exc).__name__
        props["error_message"] = str(exc)
        props["traceback"] = traceback.format_exc()
        if context:
            props.update(context)
        if hasattr(_posthog, "capture_exception"):
            _posthog.capture_exception(exc, distinct_id=_distinct_id(), properties=props)
        else:
            _posthog.capture(distinct_id=_distinct_id(), event="$exception", properties=props)
    except Exception as e:
        print(f"posthog_reporter: capture_exception failed: {e}", flush=True)


def flush() -> None:
    """Flush pending events. Call before process exit when possible."""
    _init()
    if not _enabled:
        return
    try:
        _posthog.flush()
    except Exception:
        pass


def install_global_handler(component: str) -> None:
    """Install a sys.excepthook that reports uncaught exceptions to PostHog
    before the process dies. Use as a safety net at the top of each script's
    main entry point.
    """
    def _hook(exc_type, exc_value, tb):
        try:
            capture_exception(exc_value, context={"component": component, "fatal": True})
            flush()
        finally:
            sys.__excepthook__(exc_type, exc_value, tb)
    sys.excepthook = _hook
