"""Loader for config/support.yaml (the only support module that touches the file system)."""

from __future__ import annotations

import dataclasses
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.orchestrator.support import SupportConfig
from app.registries.paths import config_dir

_FIELDS = {f.name for f in dataclasses.fields(SupportConfig)}


def support_config_from_mapping(data: dict[str, Any]) -> SupportConfig:
    """Build and validate a config; unknown keys are an error."""
    unknown = sorted(set(data) - _FIELDS)
    if unknown:
        raise ValueError(f"unknown support config keys: {', '.join(unknown)}")
    try:
        return SupportConfig(**data)
    except TypeError as exc:
        raise ValueError(f"invalid support config: {exc}") from exc


@lru_cache(maxsize=8)
def _load(path: str, mtime_ns: int) -> SupportConfig:
    del mtime_ns  # part of the cache key only
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping of support parameters")
    return support_config_from_mapping(data)


def load_support_config(path: Path | None = None) -> SupportConfig:
    """The validated config from `path`, else `<config dir>/support.yaml`."""
    target = path if path is not None else config_dir() / "support.yaml"
    return _load(str(target), target.stat().st_mtime_ns)
