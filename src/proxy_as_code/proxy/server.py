from __future__ import annotations

from proxy_as_code.capture.handler import CaptureHandler
from proxy_as_code.config import AppConfig
from proxy_as_code.proxy.addons import ProxyAsCodeAddon
from proxy_as_code.proxy.lifecycle import ProxyLifecycle
from proxy_as_code.storage.repository import TrafficRepository


class ProxyServer:
    def __init__(self, config: AppConfig, repository: TrafficRepository) -> None:
        handler = CaptureHandler(config, repository)
        addon = ProxyAsCodeAddon(handler)
        self._lifecycle = ProxyLifecycle(config.proxy, addon)

    def start(self) -> None:
        self._lifecycle.start()

    def stop(self) -> None:
        self._lifecycle.stop()
