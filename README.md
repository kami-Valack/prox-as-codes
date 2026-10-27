# Proxy as Code

HTTP/HTTPS proxy that captures traffic, stores faithful originals, compiles reusable Python/cURL artifacts, and replays requests under separate capture vs execution policies.

## Requirements

- Python 3.11+
- Clients must trust the mitmproxy CA for HTTPS interception (see [mitmproxy docs](https://docs.mitmproxy.org/stable/concepts-certificates/))

## Install

```bash
uv sync --locked --extra dev
```

The committed [`uv.lock`](uv.lock) pins the full dependency graph. To install
without uv, use `pip install -e ".[dev]"`; this resolves dependencies from the
version ranges in `pyproject.toml` rather than the lockfile.

## Configuration

Edit [`config.yaml`](config.yaml). Capture domains and replay allowed domains are **independent** security decisions.

## Run

```bash
proxy-as-code serve
```

- Proxy: `127.0.0.1:8080` (default)
- API: `http://127.0.0.1:8090/docs`

Point your browser or tool at the proxy. Only hosts matching `capture.include_domains` (and not excluded) are persisted.

## Replay approval

When `replay.require_approval` is true, API replay requires header `X-Replay-Approval: <token>` (set `replay.approval_token` in config) or CLI flag `--approved`.

## Fidelity

- **Capture fidelity**: bytes and metadata at the interception point.
- **Semantic replay**: same method, URL, headers, and body meaning via httpx.
- **Low-level replay**: best effort only; libraries may normalize URLs/headers.

Certificate pinning, mTLS, and universal HTTPS interception are not guaranteed without extra setup.

## Tests

```bash
uv run --locked pytest
```

CI runs the locked install, package build, and test suite on Python 3.11, 3.12,
and 3.13.

## Run in a container

Docker Compose builds the image, starts the proxy and API, and persists captured
data in a named volume:

```bash
docker compose up --build
```

The proxy is available at `127.0.0.1:8080` and the API docs at
`http://127.0.0.1:8090/docs`. Capturing and replaying are disabled for all
domains by default. Set the allowed domains explicitly before use, for example
in PowerShell:

```powershell
$env:PROXY_AS_CODE_CAPTURE__INCLUDE_DOMAINS='["example.com"]'
$env:PROXY_AS_CODE_REPLAY__ALLOWED_DOMAINS='["example.com"]'
docker compose up --build
```

Replay approval remains required. Stop the container with `docker compose down`;
the `proxy-data` volume is retained.

## AI agents (MCP)

With capture running via `serve`, start the MCP bridge for Cursor or other agents:

```bash
pip install -e ".[agent]"
proxy-as-code mcp
```

See [docs/agent-setup.md](docs/agent-setup.md) and [docs/cursor-mcp.example.json](docs/cursor-mcp.example.json).

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/api.md](docs/api.md)
- [docs/agent-setup.md](docs/agent-setup.md)
- [docs/threat-model.md](docs/threat-model.md)
