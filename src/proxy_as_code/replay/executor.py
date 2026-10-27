from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx

from proxy_as_code.capture.models import HeaderPair, OriginalRecord, ReplayResult
from proxy_as_code.config import AppConfig
from proxy_as_code.filtering.rules import ReplayPolicy
from proxy_as_code.replay.comparison import compare_responses
from proxy_as_code.replay.safety import ReplaySafetyGate
from proxy_as_code.storage.repository import TrafficRepository


def _headers_to_dict(headers: list[HeaderPair]) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in headers:
        if h.name.lower() == "host":
            continue
        out[h.name] = h.value
    return out


class ReplayExecutor:
    def __init__(
        self,
        config: AppConfig,
        repository: TrafficRepository,
    ) -> None:
        self._repo = repository
        self._policy = ReplayPolicy(config.replay)
        self._gate = ReplaySafetyGate(self._policy)

    def replay(
        self,
        transaction_id,
        *,
        approved: bool = False,
        approval_header: str | None = None,
        approved_by: str | None = None,
    ) -> ReplayResult:
        record = self._repo.get_transaction(transaction_id)
        if record is None:
            raise ValueError(f"Transaction not found: {transaction_id}")

        approver = self._gate.check_approval(approved, approval_header)
        self._gate.check_host(record.host)
        self._gate.check_rate_limit()

        body = self._repo.load_body(record.request_body_ref)
        headers = _headers_to_dict(record.request_headers)
        timeout = self._policy.timeout_seconds

        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                record.method,
                record.url,
                headers=headers,
                content=body,
            )

        res_body = response.content
        sent_ref = self._repo.store_body(body)
        res_ref = self._repo.store_body(res_body)
        res_header_pairs = [
            HeaderPair(name=k, value=v) for k, v in response.headers.items()
        ]

        orig_body = self._repo.load_body(record.response_body_ref)
        diff = compare_responses(
            record.response_status,
            record.response_headers,
            orig_body,
            response.status_code,
            res_header_pairs,
            res_body,
        )

        result = ReplayResult(
            id=uuid4(),
            transaction_id=record.id,
            sent_method=record.method,
            sent_url=record.url,
            sent_headers=record.request_headers,
            sent_body_ref=sent_ref,
            response_status=response.status_code,
            response_headers=res_header_pairs,
            response_body_ref=res_ref,
            diff_summary=diff,
            approved_by=approved_by or approver,
            created_at=datetime.now(timezone.utc),
        )
        self._repo.insert_replay_result(result)
        return result
