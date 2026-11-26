"""Reading draft files and writing compiled YAML (byte-stable)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.authoring.schema import DraftFile


def drafts_root(content_root: Path) -> Path:
    return content_root / "authoring" / "drafts"


def draft_files(root: Path) -> list[Path]:
    """Every `*.yaml` under the drafts folder, sorted (a stable order)."""
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.yaml"), key=lambda p: p.as_posix())


def read_draft(path: Path) -> tuple[DraftFile | None, list[str]]:
    """Parse one draft file strictly. Returns (file, errors); errors are plain sentences."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, [f"cannot read YAML: {str(exc).splitlines()[0]}"]
    if not isinstance(raw, dict):
        return None, ["the file is not a YAML mapping"]
    try:
        return DraftFile.model_validate(raw), []
    except ValidationError as exc:
        out = []
        for err in exc.errors():
            where = ".".join(str(x) for x in err["loc"]) or "file"
            out.append(f"schema: {where}: {err['msg']}")
        return None, out


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)


def write_if_changed(path: Path, text: str) -> bool:
    """Write with LF newlines; skip when identical. Returns True when the file changed."""
    if path.is_file() and path.read_bytes() == text.encode("utf-8"):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return True
