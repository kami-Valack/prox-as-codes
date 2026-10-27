from __future__ import annotations

import hashlib
from pathlib import Path


def blob_ref(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_blob(blobs_dir: Path, content: bytes) -> str:
    ref = blob_ref(content)
    path = blobs_dir / ref[:2] / ref
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return ref


def read_blob(blobs_dir: Path, ref: str | None) -> bytes | None:
    if not ref:
        return None
    path = blobs_dir / ref[:2] / ref
    if not path.is_file():
        return None
    return path.read_bytes()
