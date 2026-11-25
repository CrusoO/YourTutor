from __future__ import annotations

import os
from functools import cache
from pathlib import Path


@cache
def repo_root() -> Path:
    # cached: `resolve()` is a syscall, and validating thousands of items calls this per item
    # (it failed with WinError 1450 on a OneDrive folder)
    return Path(__file__).resolve().parents[4]


def bundled_config_dir() -> Path:
    """A copy of `<repo>/config` kept inside the API folder (`scripts/sync_bundled_config.py`).

    Vercel uploads only `apps/api`, so the real `config/` folder is not there; a test fails if this
    copy differs from it.
    """
    return Path(__file__).resolve().parents[2] / "bundled_config"


def config_dir() -> Path:
    """`CONFIG_DIR` (containers mount `/config`), else `<repo>/config`, else the bundled copy."""
    override = os.environ.get("CONFIG_DIR")
    if override:
        return Path(override)
    repo = repo_root() / "config"
    return repo if repo.is_dir() else bundled_config_dir()


def content_root() -> Path:
    """`CONTENT_DIR` (containers mount `/content`), else `<repo>/content`."""
    override = os.environ.get("CONTENT_DIR")
    return Path(override) if override else repo_root() / "content"


def bundled_curricula_dir() -> Path:
    """A copy of `<repo>/content/curricula` inside the API folder (see `bundled_config_dir`)."""
    return Path(__file__).resolve().parents[2] / "bundled_curricula"


def content_curricula_dir() -> Path:
    """`<content root>/curricula`, else the bundled copy (Vercel uploads only `apps/api`).

    Only the small curricula folder is bundled; `content_root()` itself is not redirected, so the
    reviewer desk still falls back to its snapshot when the real content folder is absent.
    """
    real = content_root() / "curricula"
    return real if real.is_dir() else bundled_curricula_dir()
