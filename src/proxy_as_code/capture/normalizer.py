from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlencode, urlparse

from mitmproxy.http import HTTPFlow

from proxy_as_code.capture.models import HeaderPair, OriginalRecord


def _header_pairs(flow_headers) -> list[HeaderPair]:
    pairs: list[HeaderPair] = []
    for name, value in flow_headers.items(multi=True):
        pairs.append(HeaderPair(name=name, value=value))
    return pairs


def flow_to_record(
    flow: HTTPFlow,
    *,
    request_body_ref: str | None,
    response_body_ref: str | None,
    captured_at: datetime | None = None,
) -> OriginalRecord:
    req = flow.request
    res = flow.response
    parsed = urlparse(req.pretty_url)
    query = parsed.query or ""
    duration_ms: float | None = None
    if flow.request.timestamp and flow.response and flow.response.timestamp:
        duration_ms = (flow.response.timestamp - flow.request.timestamp) * 1000.0

    return OriginalRecord(
        id=uuid4(),
        method=req.method,
        url=req.pretty_url,
        host=parsed.hostname or req.host or "",
        path=parsed.path or "/",
        query=query,
        scheme=parsed.scheme or "https",
        request_headers=_header_pairs(req.headers),
        request_body_ref=request_body_ref,
        response_status=res.status_code if res else None,
        response_headers=_header_pairs(res.headers) if res else [],
        response_body_ref=response_body_ref,
        captured_at=captured_at or datetime.now(timezone.utc),
        duration_ms=duration_ms,
    )


def rebuild_query(items: list[tuple[str, str]]) -> str:
    return urlencode(items, doseq=True)
