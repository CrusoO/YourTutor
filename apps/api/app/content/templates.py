"""Template schema helpers and approval hash (template + generator version)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from app.content.schema import ItemTemplate

GENERATOR_VERSION = "1"


def canonical_template_payload(template: ItemTemplate) -> dict:
    data = template.model_dump(mode="json", by_alias=True)
    for key in ("status", "reviewed_by", "content_hash"):
        data.pop(key, None)
    return data


def template_hash(template: ItemTemplate, *, generator_version: str = GENERATOR_VERSION) -> str:
    payload = {
        "template": canonical_template_payload(template),
        "generator_version": generator_version,
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_templates(root: Path) -> list[ItemTemplate]:
    folder = root / "templates"
    if not folder.exists():
        return []
    templates = []
    for path in sorted(folder.rglob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path} must contain a mapping")
        templates.append(ItemTemplate.model_validate(raw))
    return templates


def write_template(root: Path, template: ItemTemplate) -> Path:
    path = root / "templates" / f"{template.id.replace('.', '_').lower()}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = template.model_dump(mode="json", by_alias=True, exclude_none=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path
