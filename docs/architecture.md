# Architecture

Three entities are kept separate:

1. **Original Record** — captured method, URL, headers, body references, response metadata.
2. **Generated Artifact** — derived Python/cURL code referencing the original transaction ID.
3. **Replay Result** — outbound replay attempt with its own response and diff summary.

## Flow

```
Client → mitmproxy addon → CapturePolicy → CaptureHandler → SQLite + blobs
                                              ↓
                                         Compiler → artifacts table
API / AI tools → Repository
              → ReplayExecutor → ReplaySafetyGate → httpx → replay_results
```

## Fidelity levels

- **Capture**: best effort at the proxy interception point.
- **Semantic replay**: httpx resends method, URL, headers, and body content.
- **Low-level replay**: not guaranteed; documented in comparison output.

## Policies

Capture domain rules and replay allowed domains are evaluated independently.
