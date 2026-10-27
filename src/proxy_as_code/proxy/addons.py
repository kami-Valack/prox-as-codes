from __future__ import annotations

import logging

from mitmproxy.http import HTTPFlow

from proxy_as_code.capture.handler import CaptureHandler

logger = logging.getLogger(__name__)


class ProxyAsCodeAddon:
    def __init__(self, handler: CaptureHandler) -> None:
        self._handler = handler

    def load(self, loader) -> None:
        logger.info("Proxy as Code capture addon loaded")

    def requestheaders(self, flow: HTTPFlow) -> None:
        logger.info(
            "Request received by proxy: method=%s host=%s path=%s",
            flow.request.method,
            flow.request.host,
            flow.request.path.split("?", 1)[0],
        )

    def response(self, flow: HTTPFlow) -> None:
        try:
            self._handler.response(flow)
        except Exception as exc:
            logger.exception(
                "Capture processing failed: method=%s host=%s path=%s error=%s",
                flow.request.method,
                flow.request.host,
                flow.request.path.split("?", 1)[0],
                exc,
            )

    def error(self, flow: HTTPFlow) -> None:
        logger.warning(
            "Proxy request ended with an error before a response: "
            "method=%s host=%s path=%s error=%s",
            flow.request.method,
            flow.request.host,
            flow.request.path.split("?", 1)[0],
            flow.error.msg if flow.error else "unknown",
        )
