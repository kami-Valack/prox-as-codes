from __future__ import annotations

"""
Domain matching rules:
- Hosts are normalized to lowercase punycode (IDNA) without port.
- Exact patterns match the full host only (example.test does NOT match notexample.test).
- Wildcard *.api.example.test matches hosts whose full name equals api.example.test
  or ends with .api.example.test (one label substituted by *).
"""

def normalize_host(host: str) -> str:
    host = host.strip().lower()
    if ":" in host and not host.startswith("["):
        host = host.rsplit(":", 1)[0]
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return host


def _host_matches_pattern(host: str, pattern: str) -> bool:
    host = normalize_host(host)
    pattern = normalize_host(pattern)

    if pattern.startswith("*."):
        suffix = pattern[2:]
        if not suffix:
            return False
        return host == suffix or host.endswith("." + suffix)

    return host == pattern


def should_capture_host(
    host: str,
    include_domains: list[str],
    exclude_domains: list[str],
) -> bool:
    for pattern in exclude_domains:
        if _host_matches_pattern(host, pattern):
            return False
    if not include_domains:
        return False
    for pattern in include_domains:
        if _host_matches_pattern(host, pattern):
            return True
    return False


def is_replay_allowed_host(host: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return False
    for pattern in allowed_domains:
        if _host_matches_pattern(host, pattern):
            return True
    return False
