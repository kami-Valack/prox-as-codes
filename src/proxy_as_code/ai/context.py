from __future__ import annotations

from collections import Counter
from typing import Any

from proxy_as_code.app_context import AppContext


def build_session_summary(ctx: AppContext, *, last_n: int = 20) -> dict[str, Any]:
    rows = ctx.repository.search_transactions(limit=last_n)
    path_counts = Counter(f"{r.method} {r.path}" for r in rows)
    host_counts = Counter(r.host for r in rows)
    return {
        "transaction_count_sampled": len(rows),
        "top_paths": path_counts.most_common(10),
        "top_hosts": host_counts.most_common(10),
        "latest": [
            {
                "transaction_id": str(r.id),
                "method": r.method,
                "host": r.host,
                "path": r.path,
                "status": r.response_status,
            }
            for r in rows[:10]
        ],
        "note": "Facts below are observed traffic only; hypotheses require separate labeling.",
    }


def prompt_context_block(ctx: AppContext) -> str:
    summary = build_session_summary(ctx)
    lines = [
        "Proxy as Code session summary (observed traffic):",
        f"- Sampled transactions: {summary['transaction_count_sampled']}",
    ]
    for path, count in summary["top_paths"][:5]:
        lines.append(f"- {path} ({count}x)")
    lines.append("Use search_requests/get_transaction for details; replay requires policy approval.")
    return "\n".join(lines)
