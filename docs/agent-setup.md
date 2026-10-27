# AI agent pentest setup

Agents (Cursor, Claude Desktop, custom MCP clients) interact with **captured traffic** via MCP tools. They do not read raw proxy logs or the full SQLite dump.

## Architecture

1. **Terminal 1:** `proxy-as-code serve` — captures traffic into `data/proxy_as_code.db`.
2. **Terminal 2 (optional):** Cursor loads MCP — `proxy-as-code mcp` reads the same database.

The agent workflow:

1. `session_summary` or `search_requests` — pick `transaction_id`s.
2. `get_transaction` — headers + payloads (`text` or `base64`, truncated per `ai.max_body_bytes`).
3. `get_artifact` — Python/cURL replay snippet.
4. `replay_request` — only if `replay.allowed_domains` and `approval_token` / `approved=true`.
5. `compare_responses` — diff after replay.

Every tool response includes `evidence`: `observed` (capture) or `replay`.

## Install

```bash
pip install -e ".[agent]"
```

## Run MCP (stdio)

```bash
cd "/path/to/proxy as code"
proxy-as-code mcp --config config.yaml
```

## Cursor configuration (Windows + WSL)

This repo includes [`.cursor/mcp.json`](../.cursor/mcp.json) for the workspace. Cursor should pick it up when you open this folder.

If tools do not appear, merge the same block into your user file:

`C:\Users\<you>\.cursor\mcp.json`

Or paste via **Cursor Settings → MCP → Add new MCP server**.

Requirements:

- WSL user `valack` (change `-u valack` if you use another user).
- `pip install -e ".[agent]"` once in WSL so `mcp` is installed.
- `proxy-as-code serve` running while you capture; MCP only reads the DB.

Restart Cursor after changing MCP config. The agent sees tools:

| Tool | Purpose |
|------|---------|
| `session_summary` | Recent hosts/paths |
| `search_requests` | Filter transactions |
| `get_transaction` | Full HTTP + bodies |
| `get_artifact` | Python / curl code |
| `replay_request` | Controlled re-send |
| `compare_responses` | Original vs replay |
| `export_session` | ZIP export |

## Replay policy for agents

In `config.yaml`:

- `replay.allowed_domains` must include targets you authorize (independent from capture list).
- Set `replay.approval_token` and pass it to `replay_request(approval_token="...")` or use `approved=true` only in trusted lab automation.

## Pentest prompt hints

- Search by `path_prefix` (e.g. `/api/`) before opening bodies.
- Treat `Authorization` headers as redacted when `compiler.redact_sensitive_headers` is true.
- Distinguish **observed** facts from **hypotheses** in your analysis.
- Prefer `get_artifact` + manual edits over blind `replay_request` on mutating endpoints.

## REST alternative

If MCP is not used, the same data is available at `http://127.0.0.1:8090/docs` (`GET /v1/transactions/{id}` includes bodies).
