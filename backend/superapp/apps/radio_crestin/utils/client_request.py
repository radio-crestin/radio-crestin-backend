"""Who is calling: the client IP and country from Cloudflare/proxy headers."""
import ipaddress
from typing import Optional

# Cloudflare's CF-IPCountry placeholders: XX = unknown, T1 = Tor.
UNKNOWN_COUNTRIES = {'XX', 'T1'}


def client_ip(request) -> str:
    """Priority: CF-Connecting-IP (Cloudflare) -> X-Real-IP (Nginx) -> X-Forwarded-For (first hop) -> REMOTE_ADDR."""
    cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_connecting_ip:
        return cf_connecting_ip.strip()
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def safe_ip(value) -> Optional[str]:
    """A normalized IP string, or None when `value` isn't a valid IP."""
    try:
        return str(ipaddress.ip_address(value)) if value else None
    except ValueError:
        return None


def client_country(request) -> Optional[str]:
    """The ISO-2 country from CF-IPCountry, or None when missing or unknown."""
    country = (request.META.get('HTTP_CF_IPCOUNTRY') or '').strip().upper()
    if len(country) != 2 or not country.isalpha() or country in UNKNOWN_COUNTRIES:
        return None
    return country
