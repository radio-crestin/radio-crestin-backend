"""
S3 uploader — mirrors station output to S3.

Layout on S3 (mirrors local):
  <station>/hls/segments/<epoch>.ts     AAC HLS segments
  <station>/dash/manifest.mpd           DASH manifest
  <station>/dash/0/init.m4s             Opus 32k init
  <station>/dash/0/chunk-*.m4s          Opus 32k segments
  <station>/dash/1/init.m4s             Opus 96k init
  <station>/dash/1/chunk-*.m4s          Opus 96k segments
  <station>/index.m3u8                  HLS playlist
"""

import base64
import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from http.client import HTTPSConnection, HTTPConnection
from urllib.parse import quote

STATION_SLUG = os.environ.get("STATION_SLUG", "")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_REGION = os.environ.get("S3_REGION", "nbg1")
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "7"))
UPLOAD_INTERVAL = int(os.environ.get("UPLOAD_INTERVAL", "5"))

_uploaded: set[str] = set()


def _sign_v4(method, path, headers_to_sign, payload_hash, timestamp, region, service="s3"):
    datestamp = timestamp[:8]
    scope = f"{datestamp}/{region}/{service}/aws4_request"
    sorted_h = sorted(headers_to_sign.items(), key=lambda x: x[0].lower())
    canon_h = "".join(f"{k.lower()}:{v.strip()}\n" for k, v in sorted_h)
    signed_h = ";".join(k.lower() for k, _ in sorted_h)
    canon_req = f"{method}\n{quote(path, safe='/')}\n\n{canon_h}\n{signed_h}\n{payload_hash}"
    string_to_sign = f"AWS4-HMAC-SHA256\n{timestamp}\n{scope}\n{hashlib.sha256(canon_req.encode()).hexdigest()}"

    def _hmac(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    k = _hmac(_hmac(_hmac(_hmac(f"AWS4{S3_SECRET_KEY}".encode(), datestamp), region), service), "aws4_request")
    sig = hmac.new(k, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={S3_ACCESS_KEY}/{scope}, SignedHeaders={signed_h}, Signature={sig}"


def _content_type(key):
    if key.endswith(".m4s"): return "video/mp4"
    if key.endswith(".ts"): return "video/mp2t"
    if key.endswith(".mpd"): return "application/dash+xml"
    if key.endswith(".m3u8"): return "application/vnd.apple.mpegurl"
    return "application/octet-stream"


def _cache_control(key):
    if key.endswith(".m4s") or key.endswith(".ts"):
        return "public, max-age=31536000, immutable"
    return "public, max-age=5"


def upload_bytes(body: bytes, s3_key: str) -> bool:
    try:
        h = hashlib.sha256(body).hexdigest()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        host = f"{S3_BUCKET}.{S3_ENDPOINT}"
        path = f"/{s3_key}"
        hs = {"host": host, "x-amz-content-sha256": h, "x-amz-date": ts}
        auth = _sign_v4("PUT", path, hs, h, ts, S3_REGION)
        conn = HTTPSConnection(host, timeout=30)
        conn.request("PUT", path, body=body, headers={
            "Host": host, "Content-Type": _content_type(s3_key),
            "Content-Length": str(len(body)), "x-amz-content-sha256": h,
            "x-amz-date": ts, "Authorization": auth,
            "Cache-Control": _cache_control(s3_key),
        })
        r = conn.getresponse(); r.read(); conn.close()
        return r.status in (200, 201, 204)
    except Exception as e:
        print(f"S3 error {s3_key}: {e}", flush=True)
        return False


def upload_file(path: str, s3_key: str) -> bool:
    try:
        with open(path, "rb") as f:
            return upload_bytes(f.read(), s3_key)
    except FileNotFoundError:
        return False


def sync_hls():
    """Upload HLS AAC .ts segments."""
    d = "/data/hls/segments"
    try:
        for name in os.listdir(d):
            if not name.endswith(".ts"): continue
            key = f"{STATION_SLUG}/hls/segments/{name}"
            if key in _uploaded: continue
            if upload_file(f"{d}/{name}", key):
                _uploaded.add(key)
    except FileNotFoundError:
        pass


def sync_dash():
    """Upload DASH Opus fMP4 segments."""
    for rep_id in ("0", "1"):
        d = f"/data/dash/{rep_id}"
        try:
            for name in os.listdir(d):
                if not name.endswith(".m4s"): continue
                key = f"{STATION_SLUG}/dash/{rep_id}/{name}"
                if name.startswith("init"):
                    upload_file(f"{d}/{name}", key)  # always re-upload init
                    continue
                if key in _uploaded: continue
                if upload_file(f"{d}/{name}", key):
                    _uploaded.add(key)
        except FileNotFoundError:
            pass


def sync_manifests():
    """Upload playlists and manifests."""
    # DASH manifest
    upload_file("/data/dash/manifest.mpd", f"{STATION_SLUG}/dash/manifest.mpd")
    # HLS playlist from generator
    try:
        conn = HTTPConnection("127.0.0.1", 8081, timeout=5)
        conn.request("GET", "/index.m3u8")
        r = conn.getresponse()
        if r.status == 200:
            upload_bytes(r.read(), f"{STATION_SLUG}/index.m3u8")
        else:
            r.read()
        conn.close()
    except Exception:
        pass


def configure_bucket():
    """Set CORS and lifecycle on S3 bucket (idempotent)."""
    host = f"{S3_BUCKET}.{S3_ENDPOINT}"

    cors = b"""<?xml version="1.0"?>
<CORSConfiguration>
  <CORSRule>
    <AllowedOrigin>*</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>HEAD</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <MaxAgeSeconds>86400</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>"""

    lifecycle = f"""<?xml version="1.0"?>
<LifecycleConfiguration>
  <Rule>
    <ID>expire-segments</ID>
    <Filter><Prefix></Prefix></Filter>
    <Status>Enabled</Status>
    <Expiration><Days>{RETENTION_DAYS}</Days></Expiration>
  </Rule>
</LifecycleConfiguration>""".encode()

    for subpath, body, extra in [
        ("/?cors", cors, {}),
        ("/?lifecycle", lifecycle, {"Content-MD5": base64.b64encode(hashlib.md5(lifecycle).digest()).decode()}),
    ]:
        try:
            h = hashlib.sha256(body).hexdigest()
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            hs = {"host": host, "x-amz-content-sha256": h, "x-amz-date": ts}
            auth = _sign_v4("PUT", subpath.split("?")[0], hs, h, ts, S3_REGION)
            headers = {"Host": host, "Content-Type": "application/xml",
                       "Content-Length": str(len(body)), "x-amz-content-sha256": h,
                       "x-amz-date": ts, "Authorization": auth, **extra}
            conn = HTTPSConnection(host, timeout=30)
            conn.request("PUT", subpath, body=body, headers=headers)
            r = conn.getresponse(); r.read(); conn.close()
            print(f"S3 config {subpath}: {r.status}", flush=True)
        except Exception as e:
            print(f"S3 config error {subpath}: {e}", flush=True)


def main():
    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, STATION_SLUG]):
        print("S3 uploader: disabled (missing config)", flush=True)
        while True:
            time.sleep(3600)

    print(f"S3 uploader: {S3_BUCKET}.{S3_ENDPOINT}/{STATION_SLUG}/", flush=True)
    configure_bucket()

    while True:
        sync_hls()
        sync_dash()
        sync_manifests()
        time.sleep(UPLOAD_INTERVAL)


if __name__ == "__main__":
    main()
