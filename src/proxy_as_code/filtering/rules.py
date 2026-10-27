from __future__ import annotations

from proxy_as_code.config import CaptureSettings, ReplaySettings
from proxy_as_code.filtering.domains import is_replay_allowed_host, should_capture_host


class CapturePolicy:
    def __init__(self, settings: CaptureSettings) -> None:
        self._settings = settings

    def should_capture(self, host: str) -> bool:
        return should_capture_host(
            host,
            self._settings.include_domains,
            self._settings.exclude_domains,
        )

    @property
    def store_bodies(self) -> bool:
        return self._settings.store_bodies


class ReplayPolicy:
    def __init__(self, settings: ReplaySettings) -> None:
        self._settings = settings

    def is_host_allowed(self, host: str) -> bool:
        return is_replay_allowed_host(host, self._settings.allowed_domains)

    @property
    def require_approval(self) -> bool:
        return self._settings.require_approval

    @property
    def timeout_seconds(self) -> float:
        return self._settings.timeout_seconds

    @property
    def rate_limit_per_minute(self) -> int:
        return self._settings.rate_limit_per_minute

    @property
    def approval_token(self) -> str | None:
        return self._settings.approval_token
