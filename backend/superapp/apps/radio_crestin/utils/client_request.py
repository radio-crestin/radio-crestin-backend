"""Who is calling: the client IP and country from Cloudflare/proxy headers."""
import functools
import ipaddress
import os
from typing import Optional

# Cloudflare's CF-IPCountry placeholders: XX = unknown, T1 = Tor.
UNKNOWN_COUNTRIES = {'XX', 'T1'}

# Proxies whose X-Forwarded-For entries are believed: the cluster's own
# addresses (Traefik and the pods reach Django from private ranges) and
# Cloudflare's edges (https://www.cloudflare.com/ips/, the list Traefik's
# forwardedHeaders.trustedIPs also uses). TRUSTED_PROXY_CIDRS replaces the
# private part, comma-separated.
PRIVATE_PROXY_CIDRS = '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8,::1/128,fc00::/7'
CLOUDFLARE_CIDRS = (
    '173.245.48.0/20,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,141.101.64.0/18,'
    '108.162.192.0/18,190.93.240.0/20,188.114.96.0/20,197.234.240.0/22,198.41.128.0/17,'
    '162.158.0.0/15,104.16.0.0/13,104.24.0.0/14,172.64.0.0/13,131.0.72.0/22,'
    '2400:cb00::/32,2606:4700::/32,2803:f800::/32,2405:b500::/32,2405:8100::/32,'
    '2a06:98c0::/29,2c0f:f248::/32'
)


@functools.cache
def _trusted_networks():
    cidrs = os.environ.get('TRUSTED_PROXY_CIDRS') or PRIVATE_PROXY_CIDRS
    return tuple(ipaddress.ip_network(c.strip()) for c in f'{cidrs},{CLOUDFLARE_CIDRS}'.split(',') if c.strip())


def _is_trusted_proxy(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    return any(address in network for network in _trusted_networks())


def client_ip(request) -> str:
    """The address of whoever sent the request, which a client cannot forge.

    REMOTE_ADDR is the peer. Only when it is a trusted proxy (Traefik, a
    pod) are the forwarded hops read, right to left: each trusted proxy
    vouches for the hop before it, and the first untrusted one is the
    client. Traefik keeps X-Forwarded-For only from Cloudflare and replaces
    it otherwise, so a client that skips Cloudflare is seen as itself.
    CF-Connecting-IP (or X-Real-IP) is read only when nothing was forwarded,
    which only a caller inside the cluster can arrange (tests do).
    """
    remote = safe_ip(request.META.get('REMOTE_ADDR')) or ''
    if not remote or not _is_trusted_proxy(remote):
        return remote
    hops = [hop.strip() for hop in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if hop.strip()]
    for hop in reversed(hops):
        ip = safe_ip(hop)
        if ip is None:
            return remote
        if not _is_trusted_proxy(ip):
            return ip
    if hops:
        return safe_ip(hops[0]) or remote
    for header in ('HTTP_CF_CONNECTING_IP', 'HTTP_X_REAL_IP'):
        ip = safe_ip((request.META.get(header) or '').strip())
        if ip:
            return ip
    return remote


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
