"""
S3 uploader — mirrors station output to S3.

Layout on S3 (mirrors local):
  <station>/hls/aac/segments/<epoch>.ts     AAC+ HLS segments
  <station>/aac/index.m3u8                  AAC+ playlist
  <station>/master.m3u8                     Master playlist
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
S3_INDEX_PATH = "/data/s3_index.json"
# Track uploaded segment numbers per codec for the index
_uploaded_segments: dict[str, set[int]] = {"aac": set()}


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
    if key.endswith(".ts"): return "video/mp2t"
    if key.endswith(".m3u8"): return "application/vnd.apple.mpegurl"
    return "application/octet-stream"


def _cache_control(key):
    if key.endswith(".ts"):
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


def sync_segments(local_dir, s3_prefix, extension, codec):
    """Upload segments from a local directory to S3 and track in index."""
    try:
        for name in os.listdir(local_dir):
            if not name.endswith(extension):
                continue
            key = f"{STATION_SLUG}/{s3_prefix}/{name}"
            if key in _uploaded:
                # Already uploaded, still track the number
                try:
                    _uploaded_segments[codec].add(int(name.replace(extension, "")))
                except ValueError:
                    pass
                continue
            if upload_file(f"{local_dir}/{name}", key):
                _uploaded.add(key)
                try:
                    _uploaded_segments[codec].add(int(name.replace(extension, "")))
                except ValueError:
                    pass
    except FileNotFoundError:
        pass


def restore_index_from_s3():
    """On startup, list S3 objects to rebuild the segment index."""
    import json as _json
    import xml.etree.ElementTree as ET

    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, STATION_SLUG]):
        return

    print("Restoring segment index from S3...", flush=True)
    host = f"{S3_BUCKET}.{S3_ENDPOINT}"

    for codec, prefix, ext in [
        ("aac", f"{STATION_SLUG}/hls/aac/segments/", ".ts"),
    ]:
        marker = ""
        total = 0
        while True:
            try:
                path = f"/?prefix={prefix}&max-keys=1000"
                if marker:
                    path += f"&marker={marker}"
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                payload_hash = hashlib.sha256(b"").hexdigest()
                hs = {"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": ts}
                auth = _sign_v4("GET", "/", hs, payload_hash, ts, S3_REGION)
                conn = HTTPSConnection(host, timeout=30)
                conn.request("GET", path, headers={
                    "Host": host, "x-amz-content-sha256": payload_hash,
                    "x-amz-date": ts, "Authorization": auth,
                })
                r = conn.getresponse()
                body = r.read()
                conn.close()

                if r.status != 200:
                    print(f"S3 list error for {codec}: HTTP {r.status}", flush=True)
                    break

                root = ET.fromstring(body)
                ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
                keys = [e.text for e in root.findall(f".//{ns}Key") if e.text]
                truncated = root.find(f"{ns}IsTruncated")

                for key in keys:
                    name = key.rsplit("/", 1)[-1] if "/" in key else key
                    if name.endswith(ext):
                        try:
                            num = int(name.replace(ext, ""))
                            _uploaded_segments[codec].add(num)
                            _uploaded.add(key)
                            total += 1
                        except ValueError:
                            pass

                if truncated is not None and truncated.text == "true":
                    marker = keys[-1] if keys else ""
                else:
                    break
            except Exception as e:
                print(f"S3 list error for {codec}: {e}", flush=True)
                break

        print(f"  {codec}: restored {total} segments from S3", flush=True)

    write_s3_index()
    print("S3 index restored", flush=True)


def write_s3_index():
    """Write the S3 segment index for the playlist generator."""
    import json as _json
    index = {}
    for codec, nums in _uploaded_segments.items():
        if nums:
            index[codec] = {"segments": sorted(nums)}
    try:
        with open(S3_INDEX_PATH, "w") as f:
            _json.dump(index, f)
    except Exception as e:
        print(f"S3 index write error: {e}", flush=True)


def sync_metadata():
    """Upload metadata files to S3."""
    import glob as _glob
    metadata_dir = "/data/metadata"
    for f in _glob.glob(f"{metadata_dir}/**/*.json", recursive=True):
        rel = os.path.relpath(f, metadata_dir)
        key = f"{STATION_SLUG}/metadata/{rel}"
        # Always re-upload index.json (changes frequently)
        if rel == "index.json":
            upload_file(f, key)
        elif key not in _uploaded:
            # Slot files are immutable once written
            if upload_file(f, key):
                _uploaded.add(key)


def restore_metadata_from_s3():
    """Download metadata index + recent slot files from S3 on startup."""
    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, STATION_SLUG]):
        return

    print("Restoring metadata from S3...", flush=True)
    host = f"{S3_BUCKET}.{S3_ENDPOINT}"

    # Download index.json
    _download_s3_file(
        f"{STATION_SLUG}/metadata/index.json",
        "/data/metadata/index.json",
    )

    # List and download recent slot files (last 24h worth)
    import xml.etree.ElementTree as ET
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz

    now = _dt.now(_tz.utc)
    total = 0
    for day_offset in range(2):  # Today + yesterday
        day = now - _td(days=day_offset)
        prefix = f"{STATION_SLUG}/metadata/{day.strftime('%Y/%m/%d')}/"
        try:
            ts = _dt.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
            payload_hash = hashlib.sha256(b"").hexdigest()
            hs = {"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": ts}
            auth = _sign_v4("GET", "/", hs, payload_hash, ts, S3_REGION)
            conn = HTTPSConnection(host, timeout=30)
            conn.request("GET", f"/?prefix={prefix}&max-keys=100", headers={
                "Host": host, "x-amz-content-sha256": payload_hash,
                "x-amz-date": ts, "Authorization": auth,
            })
            r = conn.getresponse()
            body = r.read()
            conn.close()
            if r.status != 200:
                continue
            root = ET.fromstring(body)
            ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
            for e in root.findall(f".//{ns}Key"):
                key = e.text
                if key and key.endswith(".json"):
                    local_path = "/data/metadata/" + key.split("/metadata/", 1)[-1]
                    if _download_s3_file(key, local_path):
                        total += 1
        except Exception as e:
            print(f"metadata restore error: {e}", flush=True)

    print(f"  Restored {total} metadata slot files from S3", flush=True)


def _download_s3_file(s3_key: str, local_path: str) -> bool:
    """Download a file from S3 to local disk."""
    try:
        host = f"{S3_BUCKET}.{S3_ENDPOINT}"
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload_hash = hashlib.sha256(b"").hexdigest()
        path = f"/{s3_key}"
        hs = {"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": ts}
        auth = _sign_v4("GET", path, hs, payload_hash, ts, S3_REGION)
        conn = HTTPSConnection(host, timeout=30)
        conn.request("GET", path, headers={
            "Host": host, "x-amz-content-sha256": payload_hash,
            "x-amz-date": ts, "Authorization": auth,
        })
        r = conn.getresponse()
        body = r.read()
        conn.close()
        if r.status == 200 and body:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(body)
            return True
        return False
    except Exception as e:
        print(f"S3 download error {s3_key}: {e}", flush=True)
        return False


def sync_all():
    # AAC segments
    sync_segments("/data/hls/aac/segments", "hls/aac/segments", ".ts", "aac")
    # Metadata
    sync_metadata()
    # Playlists from generator
    for path in ("/master.m3u8", "/aac/index.m3u8"):
        try:
            conn = HTTPConnection("127.0.0.1", 8081, timeout=5)
            conn.request("GET", path)
            r = conn.getresponse()
            if r.status == 200:
                s3_path = path.lstrip("/")
                upload_bytes(r.read(), f"{STATION_SLUG}/{s3_path}")
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

    # On startup, restore state from S3
    restore_index_from_s3()
    restore_metadata_from_s3()

    while True:
        sync_all()
        write_s3_index()
        time.sleep(UPLOAD_INTERVAL)


if __name__ == "__main__":
    main()
