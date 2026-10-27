# HTTP API

Base URL default: `http://127.0.0.1:8090`

OpenAPI: `/docs`

## Endpoints

| Operation | Method | Path |
|-----------|--------|------|
| search_requests | GET | `/v1/transactions` |
| list_requests | GET | `/v1/requests?limit=100&offset=0` |
| get_transaction | GET | `/v1/transactions/{id}` |
| get_artifact | GET | `/v1/transactions/{id}/artifacts?kind=python\|curl` |
| replay_request | POST | `/v1/transactions/{id}/replay` |
| compare_responses | GET | `/v1/transactions/{id}/replays/{replay_id}/compare` |
| export_session | POST | `/v1/sessions/export` |

`GET /v1/requests` returns full captured request and response details, including
headers and bodies. Results are ordered newest first; use `limit` (1–500) and
`offset` to page through the full list. The endpoint returns an empty list when
no requests have been captured.

## Replay approval

When `replay.require_approval` is enabled, send header:

`X-Replay-Approval: <replay.approval_token>`

Responses include `transaction_id` and `evidence` (`observed` or `replay`).
