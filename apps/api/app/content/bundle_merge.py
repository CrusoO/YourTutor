"""Merge supplemental content roots (e.g. E2E mini chapter)."""

from __future__ import annotations

import os
from pathlib import Path

from app.content.schema import ContentBundle
from app.content.validator import load_bundle


def e2e_mini_enabled() -> bool:
    from app.config import settings

    if settings.e2e_mini_content:
        return True
    return os.environ.get("E2E_MINI_CONTENT", "").strip().lower() in {"1", "true", "yes"}


def mini_content_root(main_root: Path) -> Path:
    return main_root / "e2e_mini"


def merge_bundles(primary: ContentBundle, extra: ContentBundle) -> ContentBundle:
    return ContentBundle(
        skills=[*primary.skills, *extra.skills],
        items=[*primary.items, *extra.items],
        misconceptions=[*primary.misconceptions, *extra.misconceptions],
        overlays=[*primary.overlays, *extra.overlays],
        glossaries=[*primary.glossaries, *extra.glossaries],
        checkpoint_forms=[*primary.checkpoint_forms, *extra.checkpoint_forms],
        templates=[*primary.templates, *extra.templates],
    )


def load_content_bundle(root: Path) -> ContentBundle:
    bundle = load_bundle(root)
    if e2e_mini_enabled():
        mini = mini_content_root(root)
        if mini.is_dir():
            bundle = merge_bundles(bundle, load_bundle(mini))
    return bundle
