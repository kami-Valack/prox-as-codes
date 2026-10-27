from __future__ import annotations

from pathlib import Path

from proxy_as_code.mcp.server import configure, run_stdio


def run_mcp_server(config_path: Path | None = None, base_dir: Path | None = None) -> None:
    configure(config_path, base_dir)
    run_stdio()
