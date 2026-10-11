"""Locale review workflow: a human reviewer fills and approves per-language strings.

`export_locale_review` lists every learner-facing string (a mapping with an `en` key and language
codes beside it, under items, lessons and copy) that has no real translation yet, or has one
nobody has reviewed. The reviewer fills the `translation` column and marks `approve`. The import
writes it into the content file and records the review in `<content>/locale_review.yaml`, tied to
the hash of the English text, so a changed English sentence makes its translations unreviewed
again.

Nothing here translates anything. A row whose `origin` is not `human`, a blank or placeholder
translation, a sheet for another language, a stale English hash and an unlisted reviewer are all
refused, so a machine draft can never become an approved string.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.content.review import reviewer_allowlist
from app.registries.loaders import load_locales_config
from app.registries.locale_resolve import locale_text_missing

SIDECAR = "locale_review.yaml"
FOLDERS = ("items", "lessons", "copy")
COLUMNS = (
    "file",
    "path",
    "object_id",
    "status",
    "en",
    "en_hash",
    "current",
    "translation",
    "origin",
    "reviewer_notes",
    "approve",
)


def en_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _is_localized(node: Any, codes: set[str]) -> bool:
    return (
        isinstance(node, dict)
        and isinstance(node.get("en"), str)
        and set(node) <= codes
        and len(node) >= 1
    )


def _walk(node: Any, codes: set[str], path: str = "") -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if _is_localized(node, codes):
        found.append((path, node))
    elif isinstance(node, dict):
        for key, value in node.items():
            found.extend(_walk(value, codes, f"{path}.{key}" if path else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_walk(value, codes, f"{path}[{index}]"))
    return found


def _files(root: Path) -> list[Path]:
    out: list[Path] = []
    for folder in FOLDERS:
        if (root / folder).is_dir():
            out.extend(sorted((root / folder).rglob("*.yaml")))
    return out


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _ledger(root: Path) -> dict[str, Any]:
    path = root / SIDECAR
    return (_load(path) or {}) if path.exists() else {}


def _key(file: str, path: str) -> str:
    return f"{file}#{path}"


def _object_id(data: Any, path: str) -> str:
    if isinstance(data, dict) and "id" in data:
        return str(data["id"])
    if isinstance(data, dict) and path.startswith("variants["):
        index = int(path.split("[")[1].split("]")[0])
        return str(data["variants"][index].get("id", ""))
    return ""


def string_status(node: dict[str, Any], locale: str, ledger_entry: dict[str, Any] | None) -> str:
    """missing | unreviewed | approved for one string in one language."""
    if locale_text_missing(node.get(locale)):
        return "missing"
    review = (ledger_entry or {}).get(locale)
    if review and review.get("en_hash") == en_hash(node["en"]):
        return "approved"
    return "unreviewed"


def locale_report(root: Path, locale: str) -> dict[str, int]:
    codes = set(load_locales_config()[1])
    ledger = _ledger(root)
    counts = {"missing": 0, "unreviewed": 0, "approved": 0}
    for file in _files(root):
        rel = file.relative_to(root).as_posix()
        for path, node in _walk(_load(file), codes):
            counts[string_status(node, locale, ledger.get(_key(rel, path)))] += 1
    return counts


def export_locale_review(root: Path, locale: str, csv_path: Path) -> int:
    codes = set(load_locales_config()[1])
    if locale not in codes or locale == "en":
        raise ValueError(f"{locale!r} is not a language to review")
    ledger = _ledger(root)
    rows: list[dict[str, str]] = []
    for file in _files(root):
        rel = file.relative_to(root).as_posix()
        data = _load(file)
        for path, node in _walk(data, codes):
            status = string_status(node, locale, ledger.get(_key(rel, path)))
            if status == "approved":
                continue
            rows.append(
                {
                    "file": rel,
                    "path": path,
                    "object_id": _object_id(data, path),
                    "status": status,
                    "en": node["en"],
                    "en_hash": en_hash(node["en"]),
                    "current": "" if status == "missing" else str(node.get(locale, "")),
                    "translation": "",
                    "origin": "human",
                    "reviewer_notes": "",
                    "approve": "",
                }
            )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


@dataclass
class LocaleImport:
    approved: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)  # with the reason


def _set_at(data: Any, path: str, locale: str, value: str) -> bool:
    node: Any = data
    for part in path.replace("]", "").replace("[", ".").split("."):
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False
    if not isinstance(node, dict):
        return False
    node[locale] = value
    return True


def import_locale_review(csv_path: Path, root: Path, locale: str, reviewer: str) -> LocaleImport:
    if reviewer not in reviewer_allowlist():
        raise PermissionError(f"{reviewer} is not an allowlisted reviewer")
    codes = set(load_locales_config()[1])
    if locale not in codes or locale == "en":
        raise ValueError(f"{locale!r} is not a language to review")
    ledger = _ledger(root)
    out = LocaleImport()
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    cache: dict[str, Any] = {}
    for row in rows:
        if (row.get("approve") or "").strip().upper() != "Y":
            continue
        where = f"{row['file']}#{row['path']}"
        if (row.get("origin") or "").strip().lower() != "human":
            out.refused.append(f"{where}: machine drafts are never approved")
            continue
        file = root / row["file"]
        data = cache.setdefault(row["file"], _load(file))
        node = _node_at(data, row["path"], codes)
        if node is None:
            out.refused.append(f"{where}: no such string")
            continue
        if row.get("en_hash") != en_hash(node["en"]):
            out.refused.append(f"{where}: the English text changed since the sheet was exported")
            continue
        text = (row.get("translation") or "").strip() or (
            "" if locale_text_missing(node.get(locale)) else str(node[locale])
        )
        if not text or locale_text_missing(text):
            out.refused.append(f"{where}: no translation to approve")
            continue
        _set_at(data, row["path"], locale, text)
        ledger.setdefault(_key(row["file"], row["path"]), {})[locale] = {
            "reviewed_by": reviewer,
            "en_hash": en_hash(node["en"]),
        }
        out.approved.append(where)
    for name, data in cache.items():
        (root / name).write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    if out.approved:
        (root / SIDECAR).write_text(
            yaml.safe_dump(ledger, sort_keys=True, allow_unicode=True), encoding="utf-8"
        )
    return out


def _node_at(data: Any, path: str, codes: set[str]) -> dict[str, Any] | None:
    node: Any = data
    for part in path.replace("]", "").replace("[", ".").split("."):
        if isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node if _is_localized(node, codes) else None
