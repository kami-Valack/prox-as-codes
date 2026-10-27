# Proxy as Code

HTTP/HTTPS proxy that captures traffic, stores faithful originals, compiles reusable Python/cURL artifacts, and replays requests under separate capture vs execution policies.

## Requirements

- Python 3.11+
- Clients must trust the mitmproxy CA for HTTPS interception (see [mitmproxy docs](https://docs.mitmproxy.org/stable/concepts-certificates/))

## Install

```bash
pip install -e ".[dev]"
```

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
pytest
```

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
