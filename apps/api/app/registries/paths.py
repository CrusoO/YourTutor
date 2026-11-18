from __future__ import annotations

import os
from functools import cache
from pathlib import Path


@cache
def repo_root() -> Path:
    # cached: `resolve()` is a syscall, and validating thousands of items calls this per item
    # (it failed with WinError 1450 on a OneDrive folder)
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
