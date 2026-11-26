"""init and ingest: lay out the folders, read each PDF once, cache its text page by page.

Limits: pypdf extracts the text layer only. A scanned page has no text layer and is listed as
needing OCR (OCR is not built). Maths layout (fractions, roots) and fonts with broken Unicode maps
(common for Hindi) come out garbled; check a few pages by eye before trusting a stage.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.bookcheck.settings import CLASSES, SUBJECTS, Settings
from app.bookcheck.store import ensure_out, read_json, write_json

INSTALL_HINT = (
    "pypdf is not installed. Install the optional extra: pip install -e .[bookcheck] "
    "(from apps/api), or: pip install pypdf"
)


class PypdfMissing(Exception):
    pass


def load_pypdf() -> Any:
    try:
        import pypdf  # lazy: optional extra, must never be needed by the deployed API
    except ImportError as err:
        raise PypdfMissing(INSTALL_HINT) from err
    return pypdf


def init(settings: Settings) -> list[str]:
    lines = []
    for grade in CLASSES:
        for subject in SUBJECTS:
            (settings.books_dir / str(grade) / subject).mkdir(parents=True, exist_ok=True)
    ensure_out(settings)
    lines.append(f"books folder: {settings.books_dir}")
    lines.append("paste PDFs as {class}/{subject}/*.pdf inside it, for example 9/maths/")
    lines.append("subjects: maths, physics, chemistry, biology, science (combined, class 9 and 10)")
    lines.append(f"private output folder: {settings.out_dir}")
    return lines


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def discover(settings: Settings) -> tuple[list[tuple[int, str, Path]], int]:
    """(class, subject, pdf path) for each PDF in the right place, and a count of misplaced ones."""
    found: list[tuple[int, str, Path]] = []
    misplaced = 0
    if not settings.books_dir.is_dir():
        return found, misplaced
    for pdf in sorted(settings.books_dir.rglob("*")):
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            continue
        rel = pdf.relative_to(settings.books_dir).parts
        if len(rel) == 3 and rel[0].isdigit() and int(rel[0]) in CLASSES and rel[1] in SUBJECTS:
            found.append((int(rel[0]), rel[1], pdf))
        else:
            misplaced += 1
    return found, misplaced


def _extract(settings: Settings, pdf: Path, sha: str) -> dict[str, Any]:
    """Stream pages into cache/<sha>/pages.jsonl (via a temp file); return the book's meta."""
    pypdf = load_pypdf()
    folder = settings.out_dir / "cache" / sha
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "pages.jsonl.tmp"
    empty: list[int] = []
    reader = pypdf.PdfReader(str(pdf))
    if reader.is_encrypted:
        reader.decrypt("")
    total = len(reader.pages)
    with open(tmp, "w", encoding="utf-8", newline="\n") as out:
        for number in range(total):
            try:
                text = reader.pages[number].extract_text() or ""
            except Exception:  # a damaged page must not stop the book
                text = ""
            if not text.strip():
                empty.append(number + 1)
            out.write(json.dumps({"p": number + 1, "t": text}, ensure_ascii=False) + "\n")
    tmp.replace(folder / "pages.jsonl")
    meta = {"sha": sha, "pages": total, "needs_ocr": empty}
    write_json(folder / "meta.json", meta)
    return meta


def ingest(settings: Settings) -> dict[str, int]:
    """Cache every PDF not yet cached (matched by sha256). Returns counts only."""
    ensure_out(settings)
    pdfs, misplaced = discover(settings)
    counts = {"pdfs": len(pdfs), "new": 0, "skipped": 0, "failed": 0, "needs_ocr_pages": 0}
    counts["misplaced"] = misplaced
    entries: list[dict[str, Any]] = []
    for grade, subject, pdf in pdfs:
        rel = pdf.relative_to(settings.books_dir).as_posix()
        entry: dict[str, Any] = {"file": rel, "class": grade, "subject": subject}
        try:
            sha = file_sha256(pdf)
            entry["sha"] = sha
            meta = read_json(settings.out_dir / "cache" / sha / "meta.json")
            if meta is not None and (settings.out_dir / "cache" / sha / "pages.jsonl").is_file():
                counts["skipped"] += 1
            else:
                meta = _extract(settings, pdf, sha)
                counts["new"] += 1
            entry.update(pages=meta["pages"], needs_ocr=meta["needs_ocr"], status="ok")
            counts["needs_ocr_pages"] += len(meta["needs_ocr"])
        except PypdfMissing:
            raise
        except Exception as err:  # unreadable file: record the kind of failure, keep going
            counts["failed"] += 1
            entry.update(status="failed", error=type(err).__name__)
        entries.append(entry)
    write_json(settings.out_dir / "manifest.json", {"books": entries})
    return counts
