"""Subscription / userinfo handling for zixora PC.

The panel (sublink server) may return a `subscription-userinfo`
header on sublink fetch: upload, download, total, expire (unix time).
All of it is OPTIONAL. If the panel sends nothing, the UI shows
no traffic bar and no days-left number — it never fakes them.

days_left: whole days from now until `expire`; None if no expire.
traffic: (used, total, pct) in bytes; None if total is 0/absent.
"""

import time


def parse_userinfo(header_value):
    """Parse a subscription-userinfo header value like
    'upload=123; download=456; total=10737418240; expire=1790000000'.
    Returns a dict with int fields (missing -> 0) or {} on bad input."""
    if not header_value or not isinstance(header_value, str):
        return {}
    out = {}
    for part in header_value.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key in ("upload", "download", "total", "expire"):
            try:
                out[key] = int(val)
            except ValueError:
                continue
    return out


def days_left(userinfo, now=None):
    """Whole days until expiry, or None if no expiry info."""
    expire = (userinfo or {}).get("expire", 0)
    if not expire:
        return None
    now = now if now is not None else int(time.time())
    remaining = expire - now
    if remaining <= 0:
        return 0
    return remaining // 86400


def traffic_usage(userinfo):
    """Return (used_bytes, total_bytes, pct) or None if no total."""
    if not userinfo:
        return None
    total = userinfo.get("total", 0)
    if not total:
        return None
    used = userinfo.get("upload", 0) + userinfo.get("download", 0)
    pct = min(100.0, (used / total) * 100.0) if total else 0.0
    return (used, total, pct)


def format_bytes(n):
    """Human-readable bytes, e.g. 1.5 GB. No Latin-digit ban applies
    in-app (that rule is for public post copy only)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"
