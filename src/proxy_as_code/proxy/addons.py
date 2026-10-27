from __future__ import annotations

from mitmproxy import ctx

from proxy_as_code.capture.handler import CaptureHandler


class ProxyAsCodeAddon:
    def __init__(self, handler: CaptureHandler) -> None:
        self._handler = handler

    def load(self, loader) -> None:
        ctx.log.info("Proxy as Code capture addon loaded")

    def response(self, flow) -> None:
        try:
            self._handler.response(flow)
        except Exception as exc:
            ctx.log.error(f"capture failed: {exc}")
