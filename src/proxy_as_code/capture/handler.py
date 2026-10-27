from __future__ import annotations

import logging
from datetime import datetime, timezone

from mitmproxy.http import HTTPFlow

from proxy_as_code.capture.models import ArtifactKind, GeneratedArtifact
from proxy_as_code.capture.normalizer import flow_to_record
from proxy_as_code.compiler.curl import compile_curl
from proxy_as_code.compiler.python import compile_python
from proxy_as_code.config import AppConfig
from proxy_as_code.filtering.rules import CapturePolicy
from proxy_as_code.storage.repository import TrafficRepository

logger = logging.getLogger(__name__)


class CaptureHandler:
    def __init__(
        self,
        config: AppConfig,
        repository: TrafficRepository,
    ) -> None:
        self._policy = CapturePolicy(config.capture)
        self._repo = repository
        self._compiler_version = config.compiler.version
        logger.info(
            "Capture policy configured: include_domains=%s exclude_domains=%s",
            config.capture.include_domains,
            config.capture.exclude_domains,
        )

    def response(self, flow: HTTPFlow) -> None:
        host = flow.request.host
        logger.info(
            "Response received by capture handler: method=%s host=%s path=%s status=%s",
            flow.request.method,
            host,
            flow.request.path.split("?", 1)[0],
            flow.response.status_code if flow.response else "missing",
        )
        if not self._policy.should_capture(host):
            logger.info(
                "Request ignored by capture domain filter: method=%s host=%s",
                flow.request.method,
                host,
            )
            return
        logger.info("Request accepted by capture domain filter: host=%s", host)
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
        logger.info(
            "Saving captured request to database: transaction_id=%s host=%s",
            record.id,
            record.host,
        )
        self._repo.insert_transaction(record)
        logger.info(
            "Captured request saved to database: transaction_id=%s",
            record.id,
        )
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
        logger.info(
            "Capture processing completed: transaction_id=%s artifacts=2",
            record.id,
        )
