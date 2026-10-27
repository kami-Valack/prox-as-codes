from __future__ import annotations

import time
from collections import deque

from proxy_as_code.filtering.rules import ReplayPolicy


class ReplaySafetyError(Exception):
    pass


class ReplaySafetyGate:
    def __init__(self, policy: ReplayPolicy) -> None:
        self._policy = policy
        self._timestamps: deque[float] = deque()

    def check_approval(self, approved: bool, approval_header: str | None) -> str | None:
        if not self._policy.require_approval:
            return "auto"
        token = self._policy.approval_token
        if approved:
            return "cli-approved"
        if token and approval_header == token:
            return "token"
        raise ReplaySafetyError(
            "Replay requires approval: set X-Replay-Approval header or use --approved"
        )

    def check_host(self, host: str) -> None:
        if not self._policy.is_host_allowed(host):
            raise ReplaySafetyError(f"Host not allowed for replay: {host}")

    def check_rate_limit(self) -> None:
        limit = self._policy.rate_limit_per_minute
        if limit <= 0:
            return
        now = time.time()
        while self._timestamps and now - self._timestamps[0] > 60.0:
            self._timestamps.popleft()
        if len(self._timestamps) >= limit:
            raise ReplaySafetyError("Replay rate limit exceeded")
        self._timestamps.append(now)
