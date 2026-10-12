"""Explicit development endpoint validation; never anonymous cloud auth."""
from ipaddress import ip_address
from urllib.parse import urlsplit


def loopback_endpoint(value: str, *, http: bool = False) -> str:
    parsed = urlsplit(value if http else 'http://'+value)
    try:
        valid = parsed.hostname == 'localhost' or ip_address(parsed.hostname or '').is_loopback
        port = parsed.port
    except ValueError:
        valid = False
        port = None
    if (not valid or not port or parsed.username or parsed.password or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment or parsed.scheme != 'http'):
        raise ValueError('Emulator endpoint must be explicit HTTP loopback with a port')
    return value.rstrip('/')

