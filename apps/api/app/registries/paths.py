from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def config_dir() -> Path:
    return repo_root() / "config"


def content_curricula_dir() -> Path:
    return repo_root() / "content" / "curricula"
