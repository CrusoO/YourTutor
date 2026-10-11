"""Approved sources: `<content>/sources/*.yaml`. A lesson or scene may only cite an entry here."""

from __future__ import annotations

from pathlib import Path

import yaml

APPROVED_LICENCES = frozenset({"authored", "open", "permission_on_file"})


def _rows(root: Path) -> tuple[list[tuple[str, dict]], list[str]]:
    rows: list[tuple[str, dict]] = []
    errors: list[str] = []
    folder = root / "sources"
    for path in sorted(folder.glob("*.yaml")) if folder.is_dir() else []:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            entries = data["sources"]
            if not isinstance(entries, list):
                raise TypeError("sources must be a list")
        except (yaml.YAMLError, KeyError, TypeError, AttributeError) as exc:
            errors.append(f"sources {path.name}: schema.invalid ({str(exc).splitlines()[0]})")
            continue
        rows.extend((path.name, e) for e in entries if isinstance(e, dict))
    return rows, errors


def source_errors(root: Path) -> list[str]:
    """Problems in the registry itself: duplicate ids, missing fields, unapproved licences."""
    rows, errors = _rows(root)
    seen: set[str] = set()
    for name, row in rows:
        source_id = str(row.get("id") or "").strip()
        if not source_id:
            errors.append(f"sources {name}: an entry has no id")
            continue
        if source_id in seen:
            errors.append(f"sources {name}: duplicate source id {source_id}")
        seen.add(source_id)
        if row.get("licence") not in APPROVED_LICENCES:
            errors.append(
                f"sources {name}: {source_id} has licence {row.get('licence')!r}; "
                f"approved licences are {', '.join(sorted(APPROVED_LICENCES))}"
            )
    return errors


def approved_source_ids(root: Path) -> set[str]:
    rows, _ = _rows(root)
    return {
        str(row["id"]).strip()
        for _, row in rows
        if row.get("id") and row.get("licence") in APPROVED_LICENCES
    }


def source_titles(root: Path | None = None) -> dict[str, str]:
    """Approved source id -> title, for the source chips shown on explanations."""
    from app.registries.paths import content_root

    rows, _ = _rows(root or content_root())
    return {
        str(row["id"]).strip(): str(row.get("title") or row["id"])
        for _, row in rows
        if row.get("id") and row.get("licence") in APPROVED_LICENCES
    }
