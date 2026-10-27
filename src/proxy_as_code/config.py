from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxySettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8080


class CaptureSettings(BaseSettings):
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    store_bodies: bool = True


class ReplaySettings(BaseSettings):
    require_approval: bool = True
    allowed_domains: list[str] = Field(default_factory=list)
    timeout_seconds: float = 15.0
    rate_limit_per_minute: int = 30
    approval_token: str | None = None


class StorageSettings(BaseSettings):
    database_path: str = "data/proxy_as_code.db"
    blobs_dir: str = "data/blobs"


class ApiSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8090


class CompilerSettings(BaseSettings):
    version: str = "0.1.0"
    redact_sensitive_headers: bool = True


class AiSettings(BaseSettings):
    max_body_bytes: int = 524_288


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROXY_AS_CODE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    proxy: ProxySettings = Field(default_factory=ProxySettings)
    capture: CaptureSettings = Field(default_factory=CaptureSettings)
    replay: ReplaySettings = Field(default_factory=ReplaySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    compiler: CompilerSettings = Field(default_factory=CompilerSettings)
    ai: AiSettings = Field(default_factory=AiSettings)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or Path(
        __import__("os").environ.get("PROXY_AS_CODE_CONFIG_PATH", "config.yaml")
    )
    data: dict[str, Any] = {}
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                data = loaded
    return AppConfig(**data)


def resolve_paths(config: AppConfig, base_dir: Path | None = None) -> AppConfig:
    """Resolve relative storage paths against project base."""
    root = base_dir or Path.cwd()
    config.storage.database_path = str(
        (root / config.storage.database_path).resolve()
    )
    config.storage.blobs_dir = str((root / config.storage.blobs_dir).resolve())
    return config
