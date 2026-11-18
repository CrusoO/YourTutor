"""Where factory content lives under a content root, and its ledgers.

`content/<board>/<class>/<subject>/` holds one lane's skills, misconceptions, overlays and stamped
items, next to its own `factory/` folder (ledger, certificates and factory-template/1 files). The
loader and validator read the root itself exactly as before and also every such subject folder. A
root with no subject folders behaves as it always did.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.content.ledger import Ledger, ledger_path

CONTENT_FOLDERS = ("skills", "items", "misconceptions", "overlays")
# top-level folders that are never a <board> folder
RESERVED = frozenset(
    {"curricula", "rights", "sources", "copy", "factory", "glossary", "checkpoints", "blueprint"}
    | set(CONTENT_FOLDERS)
    | {"templates", "lessons", "passages"}
)
FACTORY_TEMPLATE_SCHEMA = "factory-template/1"


def subject_roots(root: Path) -> list[Path]:
    """`<root>/<board>/<class>/<subject>` folders that hold at least one content folder."""
    found: list[Path] = []
    if not root.is_dir():
        return found
    for board in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in RESERVED):
        for grade in sorted(p for p in board.iterdir() if p.is_dir()):
            for subject in sorted(p for p in grade.iterdir() if p.is_dir()):
                if any((subject / name).is_dir() for name in CONTENT_FOLDERS):
                    found.append(subject)
    return found


def content_roots(root: Path) -> list[Path]:
    """The root itself, then each subject folder."""
    return [root, *subject_roots(root)]


def content_files(root: Path, folder: str) -> list[Path]:
    """`*.yaml` directly inside `<folder>` of the root and of each subject folder (lessons,
    passages), in a stable order."""
    return [
        path
        for base in content_roots(root)
        if (base / folder).is_dir()
        for path in sorted((base / folder).glob("*.yaml"))
    ]


def is_factory_template(path: Path) -> bool:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    return isinstance(data, dict) and data.get("schema") == FACTORY_TEMPLATE_SCHEMA


def factory_template_ids(root: Path) -> set[str]:
    """Ids of factory-template/1 files under any content root (`factory/templates` or
    `templates`). They are checked by `python -m app.factory certify`, not by the validator."""
    ids: set[str] = set()
    for base in content_roots(root):
        for folder in (base / "factory" / "templates", base / "templates"):
            if not folder.is_dir():
                continue
            for path in sorted(folder.rglob("*.yaml")):
                if is_factory_template(path):
                    data = yaml.safe_load(path.read_text(encoding="utf-8"))
                    ids.add(str(data.get("id")))
    return ids


@dataclass
class LedgerView:
    stamped: set[str] = field(default_factory=set)
    suspended: set[str] = field(default_factory=set)
    problems: list[str] = field(default_factory=list)


def read_ledgers(root: Path) -> LedgerView:
    """Union of every intact ledger under the root. A broken ledger is a problem and contributes
    nothing (its stamps do not count, and nothing is suspended by it)."""
    view = LedgerView()
    for base in content_roots(root):
        path = ledger_path(base)
        if not path.is_file():
            continue
        ledger = Ledger(path)
        problems = ledger.verify()
        where = "" if base == root else f"{base.relative_to(root).as_posix()}: "
        view.problems.extend(f"{where}{p}" for p in problems)
        if not problems:
            view.stamped |= ledger.stamped_record_hashes()
            view.suspended |= ledger.suspended_ids()
    return view
