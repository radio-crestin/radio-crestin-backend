import hashlib
import hmac
from typing import Optional
from urllib.parse import urlencode
from django.conf import settings


CDN_BASE_URL = "https://cdn.radiocrestin.ro"


def get_cdn_signing_secret() -> str:
    return getattr(settings, "CDN_SIGNING_SECRET", "")


def sign_url(url: str) -> str:
    """Generate HMAC-SHA256 signature for a URL."""
    secret = get_cdn_signing_secret()
    if not secret:
        return ""
    return hmac.new(secret.encode(), url.encode(), hashlib.sha256).hexdigest()


def proxy_image_url(
    url: str | None,
    *,
    width: Optional[int] = None,
    height: Optional[int] = None,
    format: Optional[str] = None,
    quality: Optional[int] = None,
    max_age: Optional[int] = None,
) -> str | None:
    """Convert a remote image URL to a CDN-proxied URL with HMAC signature.

    Args:
        url: The original image URL to proxy.
        width: Resize width (max 2048).
        height: Resize height (max 2048).
        format: Output format — webp, avif, jpeg, png.
        quality: Output quality 1-100.
        max_age: Client-side Cache-Control max-age in seconds.

    Returns the original URL if CDN signing is not configured.
    """
    if not url:
        return url

    # Only proxy valid URLs — bare filenames (e.g. "Song Name.jpg") cause CDN 400 errors
    if not url.startswith("http://") and not url.startswith("https://"):
        return None

    secret = get_cdn_signing_secret()
    if not secret:
        return url

    sig = sign_url(url)
    params = {"url": url, "sig": sig}

    if width:
        params["w"] = width
    if height:
        params["h"] = height
    if format:
        params["f"] = format
    if quality:
        params["q"] = quality
    if max_age is not None:
        params["max_age"] = max_age

    return f"{CDN_BASE_URL}/?{urlencode(params)}"
