from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from proxy_as_code.capture.models import ArtifactKind, HeaderPair


class EvidenceKind(str, Enum):
    OBSERVED = "observed"
    REPLAY = "replay"


class TransactionSummaryOut(BaseModel):
    transaction_id: UUID
    method: str
    host: str
    path: str
    response_status: int | None
    captured_at: datetime
    evidence: EvidenceKind = EvidenceKind.OBSERVED


class TransactionDetailOut(BaseModel):
    transaction_id: UUID
    evidence: EvidenceKind = EvidenceKind.OBSERVED
    method: str
    url: str
    host: str
    path: str
    query: str
    scheme: str
    request_headers: list[HeaderPair]
    request_body: bytes | None = None
    response_status: int | None
    response_headers: list[HeaderPair]
    response_body: bytes | None = None
    captured_at: datetime
    duration_ms: float | None


class ArtifactOut(BaseModel):
    transaction_id: UUID
    kind: ArtifactKind
    content: str
    compiler_version: str
    created_at: datetime
    evidence: EvidenceKind = EvidenceKind.OBSERVED


class ReplayOut(BaseModel):
    replay_id: UUID
    transaction_id: UUID
    evidence: EvidenceKind = EvidenceKind.REPLAY
    response_status: int | None
    approved_by: str | None
    created_at: datetime
    diff_summary: dict[str, Any]


class CompareOut(BaseModel):
    transaction_id: UUID
    replay_id: UUID
    evidence: EvidenceKind = EvidenceKind.REPLAY
    diff_summary: dict[str, Any]


class ExportFilters(BaseModel):
    host: str | None = None
    method: str | None = None
    path_prefix: str | None = None
    status: int | None = None
    captured_from: datetime | None = None
    captured_to: datetime | None = None
    include_bodies: bool = False
    limit: int = Field(default=500, le=5000)


class ExportOut(BaseModel):
    transaction_count: int
    export_path: str
    transaction_ids: list[UUID]
