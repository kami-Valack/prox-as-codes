from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from proxy_as_code.api.schemas import (
    ArtifactKind,
    ArtifactOut,
    CompareOut,
    ExportFilters,
    ExportOut,
    ReplayOut,
    TransactionDetailOut,
    TransactionSummaryOut,
)
from proxy_as_code.app_context import AppContext
from proxy_as_code.replay.safety import ReplaySafetyError

router = APIRouter(prefix="/v1")

_ctx: AppContext | None = None


def set_context(ctx: AppContext) -> None:
    global _ctx
    _ctx = ctx


def get_context() -> AppContext:
    if _ctx is None:
        raise HTTPException(status_code=503, detail="Application not initialized")
    return _ctx


@router.get("/transactions", response_model=list[TransactionSummaryOut])
def search_requests(
    host: str | None = None,
    method: str | None = None,
    path: str | None = Query(None, description="Path prefix filter"),
    status: int | None = None,
    captured_from: datetime | None = Query(None, alias="from"),
    captured_to: datetime | None = Query(None, alias="to"),
    limit: int = Query(100, le=500),
    offset: int = 0,
    ctx: AppContext = Depends(get_context),
):
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
        TransactionSummaryOut(
            transaction_id=r.id,
            method=r.method,
            host=r.host,
            path=r.path,
            response_status=r.response_status,
            captured_at=r.captured_at,
        )
        for r in rows
    ]


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailOut)
def get_transaction(transaction_id: UUID, ctx: AppContext = Depends(get_context)):
    record = ctx.repository.get_transaction(transaction_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionDetailOut(
        transaction_id=record.id,
        method=record.method,
        url=record.url,
        host=record.host,
        path=record.path,
        query=record.query,
        scheme=record.scheme,
        request_headers=record.request_headers,
        request_body=ctx.repository.load_body(record.request_body_ref),
        response_status=record.response_status,
        response_headers=record.response_headers,
        response_body=ctx.repository.load_body(record.response_body_ref),
        captured_at=record.captured_at,
        duration_ms=record.duration_ms,
    )


@router.get("/transactions/{transaction_id}/artifacts", response_model=list[ArtifactOut])
def get_artifact(
    transaction_id: UUID,
    kind: ArtifactKind | None = None,
    ctx: AppContext = Depends(get_context),
):
    if ctx.repository.get_transaction(transaction_id) is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    artifacts = ctx.repository.get_artifacts(transaction_id, kind)
    return [
        ArtifactOut(
            transaction_id=a.transaction_id,
            kind=a.kind,
            content=a.content,
            compiler_version=a.compiler_version,
            created_at=a.created_at,
        )
        for a in artifacts
    ]


@router.post("/transactions/{transaction_id}/replay", response_model=ReplayOut)
def replay_request(
    transaction_id: UUID,
    ctx: AppContext = Depends(get_context),
    x_replay_approval: str | None = Header(None, alias="X-Replay-Approval"),
):
    try:
        result = ctx.replay_executor.replay(
            transaction_id,
            approval_header=x_replay_approval,
        )
    except ReplaySafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReplayOut(
        replay_id=result.id,
        transaction_id=result.transaction_id,
        response_status=result.response_status,
        approved_by=result.approved_by,
        created_at=result.created_at,
        diff_summary=result.diff_summary,
    )


@router.get(
    "/transactions/{transaction_id}/replays/{replay_id}/compare",
    response_model=CompareOut,
)
def compare_responses(
    transaction_id: UUID,
    replay_id: UUID,
    ctx: AppContext = Depends(get_context),
):
    replay = ctx.repository.get_replay_result(replay_id)
    if replay is None or replay.transaction_id != transaction_id:
        raise HTTPException(status_code=404, detail="Replay not found")
    return CompareOut(
        transaction_id=transaction_id,
        replay_id=replay_id,
        diff_summary=replay.diff_summary,
    )


@router.post("/sessions/export", response_model=ExportOut)
def export_session(body: ExportFilters, ctx: AppContext = Depends(get_context)):
    summaries = ctx.repository.search_transactions(
        host=body.host,
        method=body.method,
        path_prefix=body.path_prefix,
        status=body.status,
        captured_from=body.captured_from,
        captured_to=body.captured_to,
        limit=body.limit,
        offset=0,
    )
    export_dir = Path(ctx.config.storage.blobs_dir).parent / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    zip_path = export_dir / f"session_{stamp}.zip"

    ids: list[UUID] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for s in summaries:
            ids.append(s.id)
            record = ctx.repository.get_transaction(s.id)
            if record is None:
                continue
            payload = record.model_dump(mode="json")
            if body.include_bodies:
                payload["request_body_b64"] = _optional_b64(
                    ctx, record.request_body_ref
                )
                payload["response_body_b64"] = _optional_b64(
                    ctx, record.response_body_ref
                )
            arts = ctx.repository.get_artifacts(s.id)
            payload["artifacts"] = [a.model_dump(mode="json") for a in arts]
            zf.writestr(f"transactions/{s.id}.json", json.dumps(payload, indent=2))
        zf.writestr("manifest.json", json.dumps({"transaction_ids": [str(i) for i in ids]}, indent=2))

    return ExportOut(
        transaction_count=len(ids),
        export_path=str(zip_path),
        transaction_ids=ids,
    )


def _optional_b64(ctx: AppContext, ref: str | None) -> str | None:
    if not ref:
        return None
    import base64

    data = ctx.repository.load_body(ref)
    if data is None:
        return None
    return base64.b64encode(data).decode("ascii")


def create_api(ctx: AppContext):
    from fastapi import FastAPI

    set_context(ctx)
    app = FastAPI(title="Proxy as Code API", version="0.1.0")
    app.include_router(router)
    return app
