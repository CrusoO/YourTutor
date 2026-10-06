from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def config_dir() -> Path:
    """`CONFIG_DIR` (containers mount `/config`), else `<repo>/config`."""
    override = os.environ.get("CONFIG_DIR")
    return Path(override) if override else repo_root() / "config"


def content_root() -> Path:
    """`CONTENT_DIR` (containers mount `/content`), else `<repo>/content`."""
    override = os.environ.get("CONTENT_DIR")
    return Path(override) if override else repo_root() / "content"


def content_curricula_dir() -> Path:
    return content_root() / "curricula"
