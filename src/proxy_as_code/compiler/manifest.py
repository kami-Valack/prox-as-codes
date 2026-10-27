from __future__ import annotations

import re
from proxy_as_code.capture.models import HeaderPair

SENSITIVE_HEADERS = frozenset(
    {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization"}
)


def slug_from_path(path: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", path.strip("/")) or "root"
    return slug[:48].strip("_") or "request"


def redact_headers(
    headers: list[HeaderPair], redact: bool
) -> list[HeaderPair]:
    if not redact:
        return headers
    out: list[HeaderPair] = []
    for h in headers:
        if h.name.lower() in SENSITIVE_HEADERS:
            out.append(HeaderPair(name=h.name, value="<REDACTED>"))
        else:
            out.append(h)
    return out
