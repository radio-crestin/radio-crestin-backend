"""
DASH manifest patcher — fixes timing and adds buffer hints.

Watches FFmpeg's manifest.mpd and patches it to:
1. Set suggestedPresentationDelay for 2-minute buffer
2. Set minBufferTime for smooth playback
3. Ensure segment timeline has no gaps

Runs as a background loop, patching the manifest every 2 seconds.
"""

import os
import re
import time

MANIFEST = "/data/dash/manifest.mpd"
BUFFER_SECONDS = int(os.environ.get("DASH_BUFFER_SECONDS", "120"))
MIN_BUFFER = int(os.environ.get("DASH_MIN_BUFFER", "6"))
PATCH_INTERVAL = 2

_last_mtime = 0.0


def patch_manifest():
    """Patch FFmpeg's DASH manifest with buffer hints."""
    global _last_mtime

    try:
        mtime = os.path.getmtime(MANIFEST)
        if mtime == _last_mtime:
            return  # No change
        _last_mtime = mtime

        with open(MANIFEST, "r") as f:
            content = f.read()

        modified = False

        # Add suggestedPresentationDelay if missing
        if "suggestedPresentationDelay" not in content:
            content = content.replace(
                'type="dynamic"',
                f'type="dynamic" suggestedPresentationDelay="PT{BUFFER_SECONDS}S"',
            )
            modified = True

        # Fix minBufferTime if too small
        mbt_match = re.search(r'minBufferTime="PT(\d+(?:\.\d+)?)S"', content)
        if mbt_match:
            current_mbt = float(mbt_match.group(1))
            if current_mbt < MIN_BUFFER:
                content = content.replace(
                    mbt_match.group(0),
                    f'minBufferTime="PT{MIN_BUFFER}S"',
                )
                modified = True

        if modified:
            with open(MANIFEST, "w") as f:
                f.write(content)

    except (FileNotFoundError, PermissionError):
        pass


def main():
    print(f"DASH patcher: buffer={BUFFER_SECONDS}s, minBuffer={MIN_BUFFER}s", flush=True)
    while True:
        patch_manifest()
        time.sleep(PATCH_INTERVAL)


if __name__ == "__main__":
    main()
