"""
S3 uploader — mirrors the full station output to S3.

Uploads:
  - fMP4 segments (chunk-*.m4s, init-*.m4s) — immutable, uploaded once
  - DASH manifest (manifest.mpd) — re-uploaded every cycle
  - HLS playlists (index.m3u8, hls/low.m3u8, hls/high.m3u8) — re-uploaded every cycle

S3 layout mirrors the local layout:
  s3://<bucket>/<station_slug>/segments/init-0.m4s
  s3://<bucket>/<station_slug>/segments/chunk-0-000000001.m4s
  s3://<bucket>/<station_slug>/manifest.mpd
  s3://<bucket>/<station_slug>/index.m3u8
  s3://<bucket>/<station_slug>/hls/low.m3u8
  s3://<bucket>/<station_slug>/hls/high.m3u8
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


def _content_type_for(s3_key: str) -> str:
    if s3_key.endswith(".m4s"):
        return "video/mp4"
    elif s3_key.endswith(".mpd"):
        return "application/dash+xml"
    elif s3_key.endswith(".m3u8"):
        return "application/vnd.apple.mpegurl"
    elif s3_key.endswith(".ts"):
        return "video/mp2t"
    return "application/octet-stream"


def _cache_control_for(s3_key: str) -> str:
    """Segments are immutable. Manifests/playlists change frequently."""
    if s3_key.endswith(".m4s") or s3_key.endswith(".ts"):
        return "public, max-age=31536000, immutable"
    # Manifests and playlists: short cache so S3-hosted copies stay fresh
    return "public, max-age=5"


def upload_file(local_path: str, s3_key: str) -> bool:
    """Upload a file to S3 using raw HTTPS + AWS Signature V4."""
    try:
        with open(local_path, "rb") as f:
            body = f.read()

        content_hash = hashlib.sha256(body).hexdigest()
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")

        host = f"{S3_BUCKET}.{S3_ENDPOINT}"
        path = f"/{s3_key}"

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
                "Content-Type": _content_type_for(s3_key),
                "Content-Length": str(len(body)),
                "x-amz-content-sha256": content_hash,
                "x-amz-date": timestamp,
                "Authorization": auth,
                "Cache-Control": _cache_control_for(s3_key),
            },
        )
        resp = conn.getresponse()
        resp.read()  # drain response body
        conn.close()

        if resp.status in (200, 201, 204):
            return True
        else:
            print(f"S3 upload failed for {s3_key}: HTTP {resp.status}", flush=True)
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


PLAYLIST_URL = "http://127.0.0.1:8081"


def sync_manifests():
    """Upload DASH manifest and HLS playlists to S3 (re-uploaded every cycle)."""
    # DASH manifest
    mpd_path = "/data/manifest.mpd"
    if os.path.isfile(mpd_path):
        upload_file(mpd_path, f"{STATION_SLUG}/manifest.mpd")

    # HLS playlists — fetch from the playlist generator (it builds them dynamically)
    for path, s3_name in [
        ("/index.m3u8", "index.m3u8"),
        ("/hls/low.m3u8", "hls/low.m3u8"),
        ("/hls/high.m3u8", "hls/high.m3u8"),
    ]:
        try:
            from http.client import HTTPConnection
            conn = HTTPConnection("127.0.0.1", 8081, timeout=5)
            conn.request("GET", path)
            resp = conn.getresponse()
            if resp.status == 200:
                body = resp.read()
                s3_key = f"{STATION_SLUG}/{s3_name}"
                _upload_bytes(body, s3_key, "application/vnd.apple.mpegurl", "public, max-age=5")
            else:
                resp.read()
            conn.close()
        except Exception as e:
            pass  # Playlist generator not ready yet, skip


def _upload_bytes(body: bytes, s3_key: str, content_type: str, cache_control: str) -> bool:
    """Upload raw bytes to S3."""
    try:
        content_hash = hashlib.sha256(body).hexdigest()
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")

        host = f"{S3_BUCKET}.{S3_ENDPOINT}"
        path = f"/{s3_key}"

        headers_to_sign = {
            "host": host,
            "x-amz-content-sha256": content_hash,
            "x-amz-date": timestamp,
        }
        auth = _sign_v4("PUT", path, headers_to_sign, content_hash, timestamp, S3_REGION)

        conn = HTTPSConnection(host, timeout=30)
        conn.request("PUT", path, body=body, headers={
            "Host": host,
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "x-amz-content-sha256": content_hash,
            "x-amz-date": timestamp,
            "Authorization": auth,
            "Cache-Control": cache_control,
        })
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status in (200, 201, 204)
    except Exception:
        return False


RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "7"))
_bucket_configured = False


def configure_bucket():
    """Configure S3 bucket CORS and lifecycle (idempotent, runs once)."""
    global _bucket_configured
    if _bucket_configured:
        return

    host = f"{S3_BUCKET}.{S3_ENDPOINT}"

    # 1. Set CORS — allow all origins for HLS/DASH playback
    cors_xml = """<?xml version="1.0" encoding="UTF-8"?>
<CORSConfiguration>
  <CORSRule>
    <AllowedOrigin>*</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>HEAD</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <ExposeHeader>Content-Length</ExposeHeader>
    <ExposeHeader>Content-Range</ExposeHeader>
    <MaxAgeSeconds>86400</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>"""

    if _s3_put_config(host, "/?cors", cors_xml.encode(), "application/xml"):
        print("S3: CORS configured", flush=True)
    else:
        print("S3: CORS config failed (may already be set)", flush=True)

    # 2. Set lifecycle — auto-delete segments after RETENTION_DAYS
    lifecycle_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<LifecycleConfiguration>
  <Rule>
    <ID>expire-segments</ID>
    <Filter>
      <Prefix></Prefix>
    </Filter>
    <Status>Enabled</Status>
    <Expiration>
      <Days>{RETENTION_DAYS}</Days>
    </Expiration>
  </Rule>
</LifecycleConfiguration>"""

    lifecycle_body = lifecycle_xml.encode()
    lifecycle_md5 = hashlib.md5(lifecycle_body).digest()
    import base64
    lifecycle_md5_b64 = base64.b64encode(lifecycle_md5).decode()

    if _s3_put_config(host, "/?lifecycle", lifecycle_body, "application/xml",
                      extra_headers={"Content-MD5": lifecycle_md5_b64}):
        print(f"S3: Lifecycle configured ({RETENTION_DAYS}-day expiration)", flush=True)
    else:
        print("S3: Lifecycle config failed (may already be set)", flush=True)

    _bucket_configured = True


def _s3_put_config(host: str, path: str, body: bytes, content_type: str,
                   extra_headers: dict = None) -> bool:
    """PUT a bucket configuration (CORS, lifecycle, etc.)."""
    try:
        content_hash = hashlib.sha256(body).hexdigest()
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")

        headers_to_sign = {
            "host": host,
            "x-amz-content-sha256": content_hash,
            "x-amz-date": timestamp,
        }
        auth = _sign_v4("PUT", path.split("?")[0], headers_to_sign, content_hash, timestamp, S3_REGION)

        req_headers = {
            "Host": host,
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "x-amz-content-sha256": content_hash,
            "x-amz-date": timestamp,
            "Authorization": auth,
        }
        if extra_headers:
            req_headers.update(extra_headers)

        conn = HTTPSConnection(host, timeout=30)
        conn.request("PUT", path, body=body, headers=req_headers)
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status in (200, 204)
    except Exception as e:
        print(f"S3 config error for {path}: {e}", flush=True)
        return False


def main():
    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, STATION_SLUG]):
        print("S3 uploader: missing config, skipping (S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY required)", flush=True)
        while True:
            time.sleep(3600)

    print(f"S3 uploader started: bucket={S3_BUCKET}.{S3_ENDPOINT}, station={STATION_SLUG}", flush=True)

    # Configure bucket CORS and lifecycle on first run
    configure_bucket()

    while True:
        sync_segments()
        sync_manifests()
        time.sleep(UPLOAD_INTERVAL)


if __name__ == "__main__":
    main()
