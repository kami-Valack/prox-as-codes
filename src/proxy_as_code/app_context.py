from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from proxy_as_code.config import AppConfig, load_config, resolve_paths
from proxy_as_code.proxy.server import ProxyServer
from proxy_as_code.replay.executor import ReplayExecutor
from proxy_as_code.storage.repository import TrafficRepository


@dataclass
class AppContext:
    config: AppConfig
    repository: TrafficRepository
    replay_executor: ReplayExecutor
    proxy_server: ProxyServer | None = None

    @classmethod
    def create(
        cls,
        config_path: Path | None = None,
        base_dir: Path | None = None,
    ) -> AppContext:
        config = resolve_paths(load_config(config_path), base_dir)
        repo = TrafficRepository(
            Path(config.storage.database_path),
            Path(config.storage.blobs_dir),
        )
        executor = ReplayExecutor(config, repo)
        proxy = ProxyServer(config, repo)
        return cls(config=config, repository=repo, replay_executor=executor, proxy_server=proxy)
