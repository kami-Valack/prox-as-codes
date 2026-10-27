from __future__ import annotations

import shlex

from proxy_as_code.capture.models import HeaderPair, OriginalRecord


def _shell_escape(value: str) -> str:
    return shlex.quote(value)


def compile_curl(record: OriginalRecord, body: bytes | None) -> str:
    parts = ["curl", "-X", record.method, _shell_escape(record.url)]
    for h in record.request_headers:
        if h.name.lower() == "host":
            continue
        if h.name.lower() == "authorization":
            parts.extend(["-H", _shell_escape("Authorization: Bearer $TOKEN")])
            continue
        parts.extend(["-H", _shell_escape(f"{h.name}: {h.value}")])
    if body:
        try:
            text = body.decode("utf-8")
            parts.extend(["--data-raw", _shell_escape(text)])
        except UnicodeDecodeError:
            parts.append(f"# Binary body ({len(body)} bytes) — use --data-binary @file")
    parts.append("-i")
    return " \\\n  ".join(parts) + "\n"
