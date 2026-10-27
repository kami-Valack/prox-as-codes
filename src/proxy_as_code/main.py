from __future__ import annotations

import socket
from pathlib import Path
from uuid import UUID

import typer
import uvicorn

from proxy_as_code.api.routes import create_api
from proxy_as_code.app_context import AppContext

app = typer.Typer(name="proxy-as-code", help="Capture, compile, and replay HTTP traffic.")


def _ctx_from_opts(config: Path | None) -> AppContext:
    return AppContext.create(config_path=config)


def _check_port_available(host: str, port: int, service: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            typer.echo(
                f"{service} cannot bind {host}:{port} ({exc}). "
                f"Stop the process using that port, e.g. "
                f"`fuser -k {port}/tcp` or change config.",
                err=True,
            )
            raise typer.Exit(code=1) from exc


@app.command("serve")
def serve(
    config: Path = typer.Option(Path("config.yaml"), help="Path to config.yaml"),
) -> None:
    """Start mitmproxy and the REST API."""
    ctx = _ctx_from_opts(config)
    api = create_api(ctx)
    proxy = ctx.config.proxy
    api_cfg = ctx.config.api
    _check_port_available(proxy.host, proxy.port, "Proxy")
    _check_port_available(api_cfg.host, api_cfg.port, "API")

    proxy_started = False
    try:
        if ctx.proxy_server:
            ctx.proxy_server.start()
            proxy_started = True
            typer.echo(f"Proxy listening on {proxy.host}:{proxy.port}")

        typer.echo(f"API listening on http://{api_cfg.host}:{api_cfg.port}/docs")
        uvicorn.run(
            api,
            host=api_cfg.host,
            port=api_cfg.port,
            log_level="info",
        )
    finally:
        if proxy_started and ctx.proxy_server:
            ctx.proxy_server.stop()


@app.command("replay")
def replay_cmd(
    transaction_id: str,
    config: Path = typer.Option(Path("config.yaml")),
    approved: bool = typer.Option(False, help="Acknowledge replay policy"),
) -> None:
    ctx = _ctx_from_opts(config)
    from proxy_as_code.replay.safety import ReplaySafetyError

    try:
        result = ctx.replay_executor.replay(
            UUID(transaction_id),
            approved=approved,
        )
    except ReplaySafetyError as exc:
        typer.echo(f"Blocked: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Replay {result.id} status={result.response_status}")


@app.command("mcp")
def mcp_cmd(
    config: Path = typer.Option(Path("config.yaml"), help="Path to config.yaml"),
) -> None:
    """Run MCP server (stdio) for AI agents — reads the same SQLite as `serve`."""
    try:
        from proxy_as_code.mcp import run_mcp_server
    except ImportError as exc:
        typer.echo(
            "Install agent extras: pip install -e '.[agent]'",
            err=True,
        )
        raise typer.Exit(code=1) from exc
    run_mcp_server(config_path=config, base_dir=Path.cwd())


@app.command("export")
def export_cmd(
    config: Path = typer.Option(Path("config.yaml")),
    host: str | None = None,
    path_prefix: str | None = None,
    limit: int = 200,
) -> None:
    from proxy_as_code.ai.tools import export_session

    ctx = _ctx_from_opts(config)
    out = export_session(ctx, host=host, path_prefix=path_prefix, limit=limit)
    typer.echo(out["export_path"])


if __name__ == "__main__":
    app()
