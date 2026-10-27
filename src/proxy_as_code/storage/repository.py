from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from proxy_as_code.capture.models import (
    ArtifactKind,
    GeneratedArtifact,
    HeaderPair,
    OriginalRecord,
    ReplayResult,
    TransactionSummary,
)
from proxy_as_code.storage import blobs
from proxy_as_code.storage.database import connect, init_db

logger = logging.getLogger(__name__)


def _headers_to_json(pairs: list[HeaderPair]) -> str:
    return json.dumps([p.model_dump() for p in pairs])


def _headers_from_json(raw: str | None) -> list[HeaderPair]:
    if not raw:
        return []
    data = json.loads(raw)
    return [HeaderPair(**item) for item in data]


class TrafficRepository:
    def __init__(self, db_path: Path, blobs_dir: Path) -> None:
        self._blobs_dir = blobs_dir
        self._blobs_dir.mkdir(parents=True, exist_ok=True)
        self._conn = connect(db_path)
        init_db(self._conn)
        logger.info("Traffic database initialized: path=%s", db_path)

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    @property
    def blobs_dir(self) -> Path:
        return self._blobs_dir

    def store_body(self, content: bytes | None) -> str | None:
        if content is None or len(content) == 0:
            return None
        return blobs.write_blob(self._blobs_dir, content)

    def load_body(self, ref: str | None) -> bytes | None:
        return blobs.read_blob(self._blobs_dir, ref)

    def insert_transaction(self, record: OriginalRecord) -> None:
        logger.info(
            "Executing transaction insert: transaction_id=%s host=%s",
            record.id,
            record.host,
        )
        self._conn.execute(
            """
            INSERT INTO transactions (
                id, method, url, host, path, query, scheme,
                request_headers_json, request_body_ref,
                response_status, response_headers_json, response_body_ref,
                captured_at, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(record.id),
                record.method,
                record.url,
                record.host,
                record.path,
                record.query,
                record.scheme,
                _headers_to_json(record.request_headers),
                record.request_body_ref,
                record.response_status,
                _headers_to_json(record.response_headers),
                record.response_body_ref,
                record.captured_at.isoformat(),
                record.duration_ms,
            ),
        )
        self._conn.commit()
        logger.info("Transaction insert committed: transaction_id=%s", record.id)

    def insert_artifact(self, artifact: GeneratedArtifact) -> None:
        self._conn.execute(
            """
            INSERT INTO artifacts (
                transaction_id, kind, content, compiler_version, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(artifact.transaction_id),
                artifact.kind.value,
                artifact.content,
                artifact.compiler_version,
                artifact.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def get_transaction(self, transaction_id: UUID) -> OriginalRecord | None:
        row = self._conn.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (str(transaction_id),),
        ).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def list_transactions(
        self, *, limit: int = 100, offset: int = 0
    ) -> list[OriginalRecord]:
        rows = self._conn.execute(
            """
            SELECT * FROM transactions
            ORDER BY captured_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [self._record_from_row(row) for row in rows]

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> OriginalRecord:
        return OriginalRecord(
            id=UUID(row["id"]),
            method=row["method"],
            url=row["url"],
            host=row["host"],
            path=row["path"],
            query=row["query"],
            scheme=row["scheme"],
            request_headers=_headers_from_json(row["request_headers_json"]),
            request_body_ref=row["request_body_ref"],
            response_status=row["response_status"],
            response_headers=_headers_from_json(row["response_headers_json"]),
            response_body_ref=row["response_body_ref"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            duration_ms=row["duration_ms"],
        )

    def search_transactions(
        self,
        *,
        host: str | None = None,
        method: str | None = None,
        path_prefix: str | None = None,
        status: int | None = None,
        captured_from: datetime | None = None,
        captured_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TransactionSummary]:
        clauses: list[str] = []
        params: list[object] = []
        if host:
            clauses.append("host = ?")
            params.append(host)
        if method:
            clauses.append("method = ?")
            params.append(method.upper())
        if path_prefix:
            clauses.append("path LIKE ?")
            params.append(path_prefix if path_prefix.endswith("%") else f"{path_prefix}%")
        if status is not None:
            clauses.append("response_status = ?")
            params.append(status)
        if captured_from:
            clauses.append("captured_at >= ?")
            params.append(captured_from.isoformat())
        if captured_to:
            clauses.append("captured_at <= ?")
            params.append(captured_to.isoformat())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT id, method, host, path, response_status, captured_at
            FROM transactions {where}
            ORDER BY captured_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [
            TransactionSummary(
                id=UUID(r["id"]),
                method=r["method"],
                host=r["host"],
                path=r["path"],
                response_status=r["response_status"],
                captured_at=datetime.fromisoformat(r["captured_at"]),
            )
            for r in rows
        ]

    def get_artifacts(
        self, transaction_id: UUID, kind: ArtifactKind | None = None
    ) -> list[GeneratedArtifact]:
        if kind:
            rows = self._conn.execute(
                """
                SELECT transaction_id, kind, content, compiler_version, created_at
                FROM artifacts WHERE transaction_id = ? AND kind = ?
                """,
                (str(transaction_id), kind.value),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT transaction_id, kind, content, compiler_version, created_at
                FROM artifacts WHERE transaction_id = ?
                """,
                (str(transaction_id),),
            ).fetchall()
        return [
            GeneratedArtifact(
                transaction_id=UUID(r["transaction_id"]),
                kind=ArtifactKind(r["kind"]),
                content=r["content"],
                compiler_version=r["compiler_version"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    def insert_replay_result(self, result: ReplayResult) -> None:
        self._conn.execute(
            """
            INSERT INTO replay_results (
                id, transaction_id, sent_method, sent_url, sent_headers_json,
                sent_body_ref, response_status, response_headers_json,
                response_body_ref, diff_summary_json, approved_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(result.id),
                str(result.transaction_id),
                result.sent_method,
                result.sent_url,
                _headers_to_json(result.sent_headers),
                result.sent_body_ref,
                result.response_status,
                _headers_to_json(result.response_headers),
                result.response_body_ref,
                json.dumps(result.diff_summary),
                result.approved_by,
                result.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def get_replay_result(self, replay_id: UUID) -> ReplayResult | None:
        row = self._conn.execute(
            "SELECT * FROM replay_results WHERE id = ?",
            (str(replay_id),),
        ).fetchone()
        if row is None:
            return None
        return ReplayResult(
            id=UUID(row["id"]),
            transaction_id=UUID(row["transaction_id"]),
            sent_method=row["sent_method"],
            sent_url=row["sent_url"],
            sent_headers=_headers_from_json(row["sent_headers_json"]),
            sent_body_ref=row["sent_body_ref"],
            response_status=row["response_status"],
            response_headers=_headers_from_json(row["response_headers_json"]),
            response_body_ref=row["response_body_ref"],
            diff_summary=json.loads(row["diff_summary_json"] or "{}"),
            approved_by=row["approved_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_replays_for_transaction(self, transaction_id: UUID) -> list[ReplayResult]:
        rows = self._conn.execute(
            "SELECT id FROM replay_results WHERE transaction_id = ? ORDER BY created_at DESC",
            (str(transaction_id),),
        ).fetchall()
        out: list[ReplayResult] = []
        for row in rows:
            replay = self.get_replay_result(UUID(row["id"]))
            if replay:
                out.append(replay)
        return out
