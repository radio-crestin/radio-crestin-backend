"""
S3 segment uploader — watches for new HLS/DASH segments and uploads them to S3.

Runs as a background process alongside FFmpeg. Uploads segments as they appear,
then local cleanup removes files older than LOCAL_RETENTION_MINUTES (default 10 min).
S3 handles 7-day retention via lifecycle policy.

Segments are uploaded to: s3://<bucket>/<station_slug>/hls/segments/<num>.ts
                           s3://<bucket>/<station_slug>/dash/<file>.m4s
"""

import hashlib
import hmac
import os
import sys
import time
from datetime import datetime, timezone
from http.client import HTTPSConnection
from urllib.parse import quote

SEGMENTS_DIR = "/data/segments"
STATION_SLUG = os.environ.get("STATION_SLUG", "")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_REGION = os.environ.get("S3_REGION", "nbg1")
UPLOAD_INTERVAL = int(os.environ.get("UPLOAD_INTERVAL", "5"))

# Track uploaded files to avoid re-uploading
_uploaded: set[str] = set()


def _sign_v4(method, path, headers_to_sign, payload_hash, timestamp, region, service="s3"):
    """AWS Signature V4 signing."""
    datestamp = timestamp[:8]
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"

    # Canonical headers
    sorted_headers = sorted(headers_to_sign.items(), key=lambda x: x[0].lower())
    canonical_headers = "".join(f"{k.lower()}:{v.strip()}\n" for k, v in sorted_headers)
    signed_headers = ";".join(k.lower() for k, _ in sorted_headers)

    canonical_request = f"{method}\n{quote(path, safe='/')}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    string_to_sign = f"AWS4-HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

    def _hmac_sha256(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    signing_key = _hmac_sha256(
        _hmac_sha256(
            _hmac_sha256(
                _hmac_sha256(f"AWS4{S3_SECRET_KEY}".encode("utf-8"), datestamp),
                region,
            ),
            service,
        ),
        "aws4_request",
    )
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={S3_ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"


def upload_file(local_path: str, s3_key: str) -> bool:
    """Upload a file to S3 using raw HTTPS + AWS Signature V4."""
    try:
        with open(local_path, "rb") as f:
            body = f.read()

        content_hash = hashlib.sha256(body).hexdigest()
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")
        date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        host = f"{S3_BUCKET}.{S3_ENDPOINT}"
        path = f"/{s3_key}"

        # Determine content type
        content_type = "video/mp2t"
        if s3_key.endswith(".m4s"):
            content_type = "video/mp4"
        elif s3_key.endswith(".mpd"):
            content_type = "application/dash+xml"
        elif s3_key.endswith(".m3u8"):
            content_type = "application/vnd.apple.mpegurl"

        headers_to_sign = {
            "host": host,
            "x-amz-content-sha256": content_hash,
            "x-amz-date": timestamp,
        }

        auth = _sign_v4("PUT", path, headers_to_sign, content_hash, timestamp, S3_REGION)

        conn = HTTPSConnection(host, timeout=30)
        conn.request(
            "PUT",
            path,
            body=body,
            headers={
                "Host": host,
                "Content-Type": content_type,
                "Content-Length": str(len(body)),
                "x-amz-content-sha256": content_hash,
                "x-amz-date": timestamp,
                "Authorization": auth,
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )
        resp = conn.getresponse()
        conn.close()

        if resp.status in (200, 201, 204):
            return True
        else:
            body_text = resp.read().decode("utf-8", errors="replace")[:200]
            print(f"S3 upload failed for {s3_key}: HTTP {resp.status} {body_text}", flush=True)
            return False

    except Exception as e:
        print(f"S3 upload error for {s3_key}: {e}", flush=True)
        return False


def sync_segments():
    """Upload new fMP4 segments to S3 (shared between DASH and HLS)."""
    try:
        for name in os.listdir(SEGMENTS_DIR):
            if not name.endswith(".m4s"):
                continue
            key = f"{STATION_SLUG}/segments/{name}"
            # Always re-upload init segments (small, may change on restart)
            if name.startswith("init-"):
                local_path = os.path.join(SEGMENTS_DIR, name)
                upload_file(local_path, key)
                continue
            if key in _uploaded:
                continue
            local_path = os.path.join(SEGMENTS_DIR, name)
            if upload_file(local_path, key):
                _uploaded.add(key)
    except FileNotFoundError:
        pass


def main():
    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, STATION_SLUG]):
        print("S3 uploader: missing config, skipping (S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY required)", flush=True)
        # Sleep forever so entrypoint doesn't think we crashed
        while True:
            time.sleep(3600)

    print(f"S3 uploader started: bucket={S3_BUCKET}.{S3_ENDPOINT}, station={STATION_SLUG}", flush=True)

    while True:
        sync_segments()
        time.sleep(UPLOAD_INTERVAL)


if __name__ == "__main__":
    main()
