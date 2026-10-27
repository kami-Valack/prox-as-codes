# Threat model (summary)

## Assets

- Captured HTTP traffic (may contain credentials and PII)
- Generated replay artifacts
- Ability to send arbitrary replay requests to allowed hosts

## Trust boundaries

- **Client → proxy**: user configures device to trust mitmproxy CA; attackers with network position could MITM the client if CA is trusted broadly.
- **API consumers → replay**: replay is gated by `allowed_domains` and optional approval token.

## Controls

- Separate capture vs replay domain policies
- Optional `X-Replay-Approval` / CLI `--approved`
- Rate limit on replay (`replay.rate_limit_per_minute`)
- Sensitive header redaction in export-oriented compiler paths (configurable)

## Out of scope / limitations

- Certificate pinning and mTLS bypass
- Universal HTTPS interception without client CA trust
- Automatic safe handling of destructive replay (operator responsibility)

## Recommendations

- Run on localhost with narrow `include_domains`
- Set a strong `replay.approval_token` in shared environments
- Do not commit `data/` or exports containing real traffic
