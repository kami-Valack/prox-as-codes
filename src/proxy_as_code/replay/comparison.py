from __future__ import annotations

import difflib
import hashlib
from typing import Any

from proxy_as_code.capture.models import HeaderPair


def _header_map(headers: list[HeaderPair]) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in headers:
        key = h.name.lower()
        out[key] = h.value
    return out


def compare_responses(
    original_status: int | None,
    original_headers: list[HeaderPair],
    original_body: bytes | None,
    replay_status: int | None,
    replay_headers: list[HeaderPair],
    replay_body: bytes | None,
    *,
    body_diff_max_lines: int = 40,
) -> dict[str, Any]:
    orig_h = _header_map(original_headers)
    repl_h = _header_map(replay_headers)
    header_diff: dict[str, dict[str, str | None]] = {}
    for key in sorted(set(orig_h) | set(repl_h)):
        if orig_h.get(key) != repl_h.get(key):
            header_diff[key] = {
                "original": orig_h.get(key),
                "replay": repl_h.get(key),
            }

    ob = original_body or b""
    rb = replay_body or b""
    body_equal = ob == rb
    summary: dict[str, Any] = {
        "status": {
            "original": original_status,
            "replay": replay_status,
            "equal": original_status == replay_status,
        },
        "headers": {
            "equal": len(header_diff) == 0,
            "differences": header_diff,
        },
        "body": {
            "equal": body_equal,
            "original_sha256": hashlib.sha256(ob).hexdigest(),
            "replay_sha256": hashlib.sha256(rb).hexdigest(),
        },
    }
    if not body_equal:
        try:
            ot = ob.decode("utf-8", errors="replace")
            rt = rb.decode("utf-8", errors="replace")
            diff = list(
                difflib.unified_diff(
                    ot.splitlines(),
                    rt.splitlines(),
                    lineterm="",
                    n=2,
                )
            )[:body_diff_max_lines]
            summary["body"]["text_diff"] = diff
        except Exception:
            summary["body"]["text_diff"] = ["<binary or undiffable>"]
    return summary
