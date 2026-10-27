from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from proxy_as_code.ai import context as ai_context
from proxy_as_code.ai import tools as ai_tools
from proxy_as_code.app_context import AppContext

mcp = FastMCP(
    "proxy-as-code",
    instructions=(
        "HTTP pentest assistant backed by Proxy as Code. "
        "Always start with search_requests or session_summary. "
        "Open one transaction at a time with get_transaction. "
        "Use get_artifact for replay code. "
        "replay_request requires replay policy (allowed_domains + approval_token or approved=true). "
        "Label evidence: observed=capture, replay=re-execution. "
        "Do not dump entire history in one call."
    ),
)

_config_path: Path | None = None
_base_dir: Path | None = None


def configure(config_path: Path | None, base_dir: Path | None = None) -> None:
    global _config_path, _base_dir
    _config_path = config_path
    _base_dir = base_dir


def _ctx() -> AppContext:
    return AppContext.create(config_path=_config_path, base_dir=_base_dir)


@mcp.tool()
def session_summary(last_n: int = 20) -> dict:
    """Short overview of recent captured traffic for orientation."""
    return ai_context.build_session_summary(_ctx(), last_n=last_n)


@mcp.tool()
def search_requests(
    host: str | None = None,
    method: str | None = None,
    path_prefix: str | None = None,
    status: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Search captured transactions (metadata only). Returns transaction_id list."""
    return ai_tools.search_requests(
        _ctx(),
        host=host,
        method=method,
        path=path_prefix,
        status=status,
        limit=min(limit, 200),
        offset=offset,
    )


@mcp.tool()
def get_transaction(
    transaction_id: str,
    include_bodies: bool = True,
) -> dict:
    """Full request/response for one transaction including payloads (base64/text, may truncate)."""
    return ai_tools.get_transaction(
        _ctx(),
        transaction_id,
        include_bodies=include_bodies,
    )


@mcp.tool()
def get_artifact(transaction_id: str, kind: str = "python") -> dict:
    """Generated Python or curl replay code for a transaction. kind: python | curl."""
    return ai_tools.get_artifact(_ctx(), transaction_id, kind=kind)


@mcp.tool()
def replay_request(
    transaction_id: str,
    approved: bool = False,
    approval_token: str | None = None,
) -> dict:
    """Re-execute a captured request under replay policy. Set approved=true or pass approval_token."""
    return ai_tools.replay_request(
        _ctx(),
        transaction_id,
        approved=approved,
        approval_token=approval_token,
    )


@mcp.tool()
def compare_responses(transaction_id: str, replay_id: str) -> dict:
    """Compare original response vs replay diff_summary."""
    return ai_tools.compare_responses(_ctx(), transaction_id, replay_id)


@mcp.tool()
def export_session(
    host: str | None = None,
    path_prefix: str | None = None,
    limit: int = 200,
) -> dict:
    """Export filtered session to ZIP under data/exports/."""
    return ai_tools.export_session(
        _ctx(),
        host=host,
        path_prefix=path_prefix,
        limit=min(limit, 500),
    )


def run_stdio() -> None:
    mcp.run(transport="stdio")
