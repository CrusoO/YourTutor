"""Versioned consent wording, one Markdown file per scope, version, language and audience.

Layout: `<config>/consent_texts/<scope>/v<N>.<lang>.<audience>.md`, audience `guardian` or `child`.
`MANIFEST.json` lists every file with the sha256 of its bytes (CRLF read as LF), so a consent record
can store exactly which wording the guardian saw. Old versions are never edited, so an old hash
always still resolves. All wording is a draft until the owner approves it by merging; nothing here
is legal advice.

Standard library only. Commands:
    python -m app.auth.consent_texts manifest   # write MANIFEST.json
    python -m app.auth.consent_texts verify     # exit 1 when files and manifest differ
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

MANIFEST_NAME = "MANIFEST.json"
AUDIENCES = ("guardian", "child")
_FILE = re.compile(r"^v(?P<n>[0-9]+)\.(?P<lang>[a-z]{2,3})\.(?P<audience>guardian|child)\.md$")


def texts_root(root: Path | None = None) -> Path:
    """`root`, else `CONFIG_DIR/consent_texts`, else `<repo>/config/consent_texts`."""
    if root is not None:
        return root
    override = os.environ.get("CONFIG_DIR")
    base = Path(override) if override else Path(__file__).resolve().parents[4] / "config"
    return base / "consent_texts"


def file_sha256(path: Path) -> str:
    """sha256 of the file bytes with CRLF turned into LF (so Windows checkouts hash the same)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def scan(root: Path | None = None) -> list[dict[str, str]]:
    """Every consent text file on disk, sorted, with its hash."""
    base = texts_root(root)
    entries: list[dict[str, str]] = []
    if not base.is_dir():
        return entries
    for scope_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for path in sorted(scope_dir.iterdir()):
            match = _FILE.match(path.name)
            if not match:
                continue
            entries.append(
                {
                    "scope": scope_dir.name,
                    "version": f"v{int(match['n'])}",
                    "lang": match["lang"],
                    "audience": match["audience"],
                    "sha256": file_sha256(path),
                }
            )
    return entries


def _dump(entries: list[dict[str, str]]) -> str:
    return json.dumps({"texts": entries}, indent=2, sort_keys=True) + "\n"


def write_manifest(root: Path | None = None) -> Path:
    target = texts_root(root) / MANIFEST_NAME
    target.write_bytes(_dump(scan(root)).encode("utf-8"))  # LF on every platform
    return target


def load_manifest(root: Path | None = None) -> list[dict[str, str]] | None:
    path = texts_root(root) / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [dict(e) for e in data["texts"]]
    except (ValueError, KeyError, TypeError):
        return None


def verify(root: Path | None = None) -> list[str]:
    """Differences between the files and MANIFEST.json (empty list: they agree)."""
    manifest = load_manifest(root)
    if manifest is None:
        return [f"{MANIFEST_NAME} is missing or unreadable"]

    def key(e: dict[str, str]) -> tuple[str, str, str, str]:
        return e["scope"], e["version"], e["lang"], e["audience"]

    listed = {key(e): e["sha256"] for e in manifest}
    on_disk = {key(e): e["sha256"] for e in scan(root)}
    problems = []
    for k in sorted(listed.keys() - on_disk.keys()):
        problems.append(f"in manifest but no file: {'/'.join(k)}")
    for k in sorted(on_disk.keys() - listed.keys()):
        problems.append(f"file not in manifest: {'/'.join(k)}")
    for k in sorted(listed.keys() & on_disk.keys()):
        if listed[k] != on_disk[k]:
            problems.append(f"hash differs: {'/'.join(k)}")
    return problems


def current_manifest(
    text_scope: str, *, lang: str = "en", root: Path | None = None
) -> dict[str, Any] | None:
    """The newest version of a scope's wording as `{version, lang, sha256: {audience: hash}}`.

    None when the scope has no text, a text lacks an audience, or the manifest and the files
    disagree about that version (nothing unverified is ever recorded as shown).
    """
    manifest = load_manifest(root)
    if manifest is None:
        return None
    mine = [e for e in manifest if e["scope"] == text_scope and e["lang"] == lang]
    if not mine:
        return None
    newest = max(mine, key=lambda e: int(e["version"][1:]))["version"]
    hashes = {e["audience"]: e["sha256"] for e in mine if e["version"] == newest}
    if set(hashes) != set(AUDIENCES):
        return None
    on_disk = {
        e["audience"]: e["sha256"]
        for e in scan(root)
        if e["scope"] == text_scope and e["lang"] == lang and e["version"] == newest
    }
    if on_disk != hashes:
        return None
    return {"version": newest, "lang": lang, "sha256": hashes}


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""
    if command == "manifest":
        print(f"wrote {write_manifest()}")
        return 0
    if command == "verify":
        problems = verify()
        for line in problems:
            print(line)
        return 1 if problems else 0
    print("usage: python -m app.auth.consent_texts manifest|verify")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
