from __future__ import annotations

from datetime import datetime, timezone

from mitmproxy.http import HTTPFlow

from proxy_as_code.capture.models import ArtifactKind, GeneratedArtifact
from proxy_as_code.capture.normalizer import flow_to_record
from proxy_as_code.compiler.curl import compile_curl
from proxy_as_code.compiler.python import compile_python
from proxy_as_code.config import AppConfig
from proxy_as_code.filtering.rules import CapturePolicy
from proxy_as_code.storage.repository import TrafficRepository


class CaptureHandler:
    def __init__(
        self,
        config: AppConfig,
        repository: TrafficRepository,
    ) -> None:
        self._policy = CapturePolicy(config.capture)
        self._repo = repository
        self._compiler_version = config.compiler.version

    def response(self, flow: HTTPFlow) -> None:
        host = flow.request.host
        if not self._policy.should_capture(host):
            return
        req_body = flow.request.raw_content or b""
        res_body = flow.response.raw_content if flow.response else b""
        req_ref = self._repo.store_body(req_body) if self._policy.store_bodies else None
        res_ref = self._repo.store_body(res_body) if self._policy.store_bodies else None
        record = flow_to_record(
            flow,
            request_body_ref=req_ref,
            response_body_ref=res_ref,
            captured_at=datetime.now(timezone.utc),
        )
        self._repo.insert_transaction(record)
        req_bytes = req_body if self._policy.store_bodies else None
        py_content = compile_python(record, req_bytes)
        curl_content = compile_curl(record, req_bytes)
        now = datetime.now(timezone.utc)
        for kind, content in (
            (ArtifactKind.PYTHON, py_content),
            (ArtifactKind.CURL, curl_content),
        ):
            self._repo.insert_artifact(
                GeneratedArtifact(
                    transaction_id=record.id,
                    kind=kind,
                    content=content,
                    compiler_version=self._compiler_version,
                    created_at=now,
                )
            )
