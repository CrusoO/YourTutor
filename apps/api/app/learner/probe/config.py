"""Loader for config/probe.yaml. The only module here that touches the file system.

The YAML file is the single place the numbers live. The cache is keyed by the file's mtime, so an
edit is picked up without a restart and an unchanged file is parsed once.
"""

from __future__ import annotations

import dataclasses
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.learner.probe.types import ProbeConfig
from app.registries.paths import config_dir

_FIELDS = {f.name for f in dataclasses.fields(ProbeConfig)}
_TUPLE_FIELDS = ("prior_bases", "prior_clip")


def config_from_mapping(data: dict[str, Any]) -> ProbeConfig:
    """Build and validate a config; unknown keys are an error (a typo must not pass silently)."""
    unknown = sorted(set(data) - _FIELDS)
    if unknown:
        raise ValueError(f"unknown probe config keys: {', '.join(unknown)}")
    values = dict(data)
    for name in _TUPLE_FIELDS:
        if name in values:
            values[name] = tuple(values[name])
    try:
        return ProbeConfig(**values)
    except TypeError as exc:  # a required key is missing
        raise ValueError(f"invalid probe config: {exc}") from exc


@lru_cache(maxsize=8)
def _load(path: str, mtime_ns: int) -> ProbeConfig:
    del mtime_ns  # part of the cache key only
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping of probe parameters")
    return config_from_mapping(data)


def load_probe_config(path: Path | None = None) -> ProbeConfig:
    """The validated probe config from `path`, else `<config dir>/probe.yaml`."""
    target = path if path is not None else config_dir() / "probe.yaml"
    return _load(str(target), target.stat().st_mtime_ns)
