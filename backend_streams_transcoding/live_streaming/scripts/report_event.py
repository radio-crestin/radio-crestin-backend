"""
CLI shim so bash can fire PostHog events.

Usage:
  python3 report_event.py <event_name> [--prop key=value ...]

Example (from entrypoint.sh):
  python3 /app/scripts/report_event.py ffmpeg_exit \
      --prop exit_code=1 --prop ran_for=12 --prop restart_count=5
"""

import sys

import posthog_reporter


def _parse_props(argv: list[str]) -> dict:
    props: dict = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--prop" and i + 1 < len(argv):
            kv = argv[i + 1]
            if "=" in kv:
                k, v = kv.split("=", 1)
                # Best-effort numeric coercion so PostHog can chart numbers
                try:
                    if "." in v:
                        v = float(v)
                    else:
                        v = int(v)
                except ValueError:
                    pass
                props[k] = v
            i += 2
        else:
            i += 1
    return props


def main():
    if len(sys.argv) < 2:
        print("usage: report_event.py <event_name> [--prop key=value ...]", file=sys.stderr)
        sys.exit(2)
    event = sys.argv[1]
    props = _parse_props(sys.argv[2:])
    posthog_reporter.capture_event(event, props)
    posthog_reporter.flush()


if __name__ == "__main__":
    main()
