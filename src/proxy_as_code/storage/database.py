from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    host TEXT NOT NULL,
    path TEXT NOT NULL,
    query TEXT NOT NULL DEFAULT '',
    scheme TEXT NOT NULL,
    request_headers_json TEXT NOT NULL,
    request_body_ref TEXT,
    response_status INTEGER,
    response_headers_json TEXT,
    response_body_ref TEXT,
    captured_at TEXT NOT NULL,
    duration_ms REAL
);

CREATE INDEX IF NOT EXISTS idx_transactions_host_path ON transactions(host, path);
CREATE INDEX IF NOT EXISTS idx_transactions_captured_at ON transactions(captured_at);
CREATE INDEX IF NOT EXISTS idx_transactions_method ON transactions(method);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    compiler_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_tx ON artifacts(transaction_id, kind);

CREATE TABLE IF NOT EXISTS replay_results (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    sent_method TEXT NOT NULL,
    sent_url TEXT NOT NULL,
    sent_headers_json TEXT NOT NULL,
    sent_body_ref TEXT,
    response_status INTEGER,
    response_headers_json TEXT,
    response_body_ref TEXT,
    diff_summary_json TEXT NOT NULL DEFAULT '{}',
    approved_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE INDEX IF NOT EXISTS idx_replay_tx ON replay_results(transaction_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
