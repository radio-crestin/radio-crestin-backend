import hashlib
import hmac
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


def proxy_image_url(url: str | None) -> str | None:
    """Convert a remote image URL to a CDN-proxied URL with HMAC signature.

    Returns the original URL if CDN signing is not configured.
    """
    if not url:
        return url

    secret = get_cdn_signing_secret()
    if not secret:
        return url

    sig = sign_url(url)
    params = urlencode({"url": url, "sig": sig})
    return f"{CDN_BASE_URL}/?{params}"
