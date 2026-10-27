from __future__ import annotations

import threading
from typing import Callable

from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster

from proxy_as_code.config import ProxySettings
from proxy_as_code.proxy.addons import ProxyAsCodeAddon


class ProxyLifecycle:
    def __init__(
        self,
        settings: ProxySettings,
        addon: ProxyAsCodeAddon,
    ) -> None:
        self._settings = settings
        self._addon = addon
        self._thread: threading.Thread | None = None
        self._master: DumpMaster | None = None
        self._loop = None

    async def _run_master(self) -> None:
        opts = options.Options(
            listen_host=self._settings.host,
            listen_port=self._settings.port,
        )
        self._master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        self._master.addons.add(self._addon)
        await self._master.run()

    def _thread_target(self) -> None:
        import asyncio

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_master())
        finally:
            self._loop.close()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_target, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._master and self._loop and not self._loop.is_closed():
            def _shutdown() -> None:
                if self._master:
                    self._master.shutdown()

            try:
                self._loop.call_soon_threadsafe(_shutdown)
            except RuntimeError:
                pass
        if self._thread:
            self._thread.join(timeout=5.0)
