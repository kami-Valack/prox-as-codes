from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ArtifactKind(str, Enum):
    PYTHON = "python"
    CURL = "curl"


class HeaderPair(BaseModel):
    name: str
    value: str


class OriginalRecord(BaseModel):
    """Faithful capture at the interception point."""

    id: UUID
    method: str
    url: str
    host: str
    path: str
    query: str
    scheme: str
    request_headers: list[HeaderPair]
    request_body_ref: str | None = None
    response_status: int | None = None
    response_headers: list[HeaderPair] = Field(default_factory=list)
    response_body_ref: str | None = None
    captured_at: datetime
    duration_ms: float | None = None


class GeneratedArtifact(BaseModel):
    transaction_id: UUID
    kind: ArtifactKind
    content: str
    compiler_version: str
    created_at: datetime


class ReplayResult(BaseModel):
    id: UUID
    transaction_id: UUID
    sent_method: str
    sent_url: str
    sent_headers: list[HeaderPair]
    sent_body_ref: str | None
    response_status: int | None
    response_headers: list[HeaderPair]
    response_body_ref: str | None
    diff_summary: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    created_at: datetime


class TransactionSummary(BaseModel):
    id: UUID
    method: str
    host: str
    path: str
    response_status: int | None
    captured_at: datetime
