from __future__ import annotations

import base64
from typing import Any


def encode_body_for_agent(
    data: bytes | None,
    *,
    max_bytes: int,
) -> dict[str, Any]:
    if data is None or len(data) == 0:
        return {"present": False, "size_bytes": 0}

    truncated = len(data) > max_bytes
    chunk = data[:max_bytes] if max_bytes > 0 else b""
    out: dict[str, Any] = {
        "present": True,
        "size_bytes": len(data),
        "truncated": truncated,
        "base64": base64.b64encode(chunk).decode("ascii"),
    }
    try:
        text = chunk.decode("utf-8")
        if "\x00" not in text:
            out["text"] = text
    except UnicodeDecodeError:
        out["text"] = None
    return out
