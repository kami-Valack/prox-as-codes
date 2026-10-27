from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from proxy_as_code.ai.bodies import encode_body_for_agent
from proxy_as_code.app_context import AppContext
from proxy_as_code.capture.models import ArtifactKind, HeaderPair
from proxy_as_code.compiler.manifest import redact_headers


def _header_payload(headers: list[HeaderPair], redact: bool) -> list[dict[str, str]]:
    pairs = redact_headers(headers, redact) if redact else headers
    return [h.model_dump() for h in pairs]


def search_requests(
    ctx: AppContext,
    *,
    host: str | None = None,
    method: str | None = None,
    path: str | None = None,
    status: int | None = None,
    captured_from: datetime | None = None,
    captured_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    rows = ctx.repository.search_transactions(
        host=host,
        method=method,
        path_prefix=path,
        status=status,
        captured_from=captured_from,
        captured_to=captured_to,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "transaction_id": str(r.id),
            "method": r.method,
            "host": r.host,
            "path": r.path,
            "response_status": r.response_status,
            "captured_at": r.captured_at.isoformat(),
            "evidence": "observed",
        }
        for r in rows
    ]


def get_transaction(
    ctx: AppContext,
    transaction_id: UUID | str,
    *,
    include_bodies: bool = True,
    redact_sensitive_headers: bool | None = None,
) -> dict[str, Any]:
    tid = transaction_id if isinstance(transaction_id, UUID) else UUID(transaction_id)
    record = ctx.repository.get_transaction(tid)
    if record is None:
        raise ValueError(f"Transaction not found: {tid}")

    redact = (
        ctx.config.compiler.redact_sensitive_headers
        if redact_sensitive_headers is None
        else redact_sensitive_headers
    )
    max_body = ctx.config.ai.max_body_bytes

    payload: dict[str, Any] = {
        "transaction_id": str(record.id),
        "evidence": "observed",
        "method": record.method,
        "url": record.url,
        "host": record.host,
        "path": record.path,
        "query": record.query,
        "scheme": record.scheme,
        "request_headers": _header_payload(record.request_headers, redact),
        "response_status": record.response_status,
        "response_headers": _header_payload(record.response_headers, redact),
        "captured_at": record.captured_at.isoformat(),
        "duration_ms": record.duration_ms,
    }
    if include_bodies:
        req = ctx.repository.load_body(record.request_body_ref)
        res = ctx.repository.load_body(record.response_body_ref)
        payload["request_body"] = encode_body_for_agent(req, max_bytes=max_body)
        payload["response_body"] = encode_body_for_agent(res, max_bytes=max_body)
    return payload


def get_artifact(
    ctx: AppContext,
    transaction_id: UUID | str,
    kind: str = "python",
) -> dict[str, Any]:
    tid = transaction_id if isinstance(transaction_id, UUID) else UUID(transaction_id)
    ak = ArtifactKind(kind)
    arts = ctx.repository.get_artifacts(tid, ak)
    if not arts:
        raise ValueError(f"No {kind} artifact for {tid}")
    a = arts[-1]
    return {
        "transaction_id": str(a.transaction_id),
        "kind": a.kind.value,
        "content": a.content,
        "compiler_version": a.compiler_version,
        "evidence": "observed",
    }


def replay_request(
    ctx: AppContext,
    transaction_id: UUID | str,
    *,
    approved: bool = False,
    approval_token: str | None = None,
) -> dict[str, Any]:
    tid = transaction_id if isinstance(transaction_id, UUID) else UUID(transaction_id)
    token = approval_token or ctx.config.replay.approval_token
    result = ctx.replay_executor.replay(
        tid,
        approved=approved,
        approval_header=token,
    )
    return {
        "replay_id": str(result.id),
        "transaction_id": str(result.transaction_id),
        "evidence": "replay",
        "response_status": result.response_status,
        "approved_by": result.approved_by,
        "diff_summary": result.diff_summary,
    }


def compare_responses(
    ctx: AppContext,
    transaction_id: UUID | str,
    replay_id: UUID | str,
) -> dict[str, Any]:
    tid = transaction_id if isinstance(transaction_id, UUID) else UUID(transaction_id)
    rid = replay_id if isinstance(replay_id, UUID) else UUID(replay_id)
    replay = ctx.repository.get_replay_result(rid)
    if replay is None or replay.transaction_id != tid:
        raise ValueError("Replay not found")
    return {
        "transaction_id": str(tid),
        "replay_id": str(rid),
        "evidence": "replay",
        "diff_summary": replay.diff_summary,
    }


def export_session(
    ctx: AppContext,
    *,
    host: str | None = None,
    path_prefix: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    from proxy_as_code.api.routes import export_session as _export
    from proxy_as_code.api.schemas import ExportFilters

    out = _export(ExportFilters(host=host, path_prefix=path_prefix, limit=limit), ctx)
    return out.model_dump(mode="json")
