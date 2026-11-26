"""report: one private Markdown file summarising every stage. It may name book headings and pages,
so it lives only in the private output folder. The returned counts are safe to print."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bookcheck.settings import Settings
from app.bookcheck.store import load_books, read_json, read_jsonl


def _scopes(settings: Settings) -> list[str]:
    names: set[str] = set()
    for folder in ("coverage", "findings", "overlap"):
        for path in (settings.out_dir / folder).glob("*"):
            names.add(path.stem)
    return sorted(names)


def build_report(settings: Settings) -> dict[str, Any]:
    books = load_books(settings)
    lines = ["# Book-check report (private: do not commit or share)", ""]
    lines.append(f"Books cached: {len(books)}")
    manifest = read_json(settings.out_dir / "manifest.json", {"books": []})
    for row in manifest["books"]:
        ocr = row.get("needs_ocr", [])
        lines.append(
            f"- {row.get('file')}: {row.get('pages', '?')} pages, needs OCR: {ocr or 'none'}"
        )
    totals = {"findings": 0, "conflicts": 0, "overlaps": 0}
    for scope in _scopes(settings):
        lines += ["", f"## {scope}"]
        cov = read_json(settings.out_dir / "coverage" / f"{scope}.json")
        if cov:
            weak = [t["key"] for t in cov["topics"] if not t["match"] or t["match"]["score"] < 0.5]
            lines.append(
                f"Coverage: {len(cov['topics'])} topics, no book match for: {weak or 'none'}"
            )
        rows = read_jsonl(settings.out_dir / "findings" / f"{scope}.jsonl")
        if rows:
            lines.append("Findings:")
            for row in rows:
                if row["verdict"] == "agree":
                    continue
                lines.append(
                    f"- {row['item_id']} [{row['topic']}] {row['verdict']} ({row['reason']})"
                    f" page {row.get('page', '-')}: {row.get('snippet', '')}"
                )
            totals["findings"] += len(rows)
            totals["conflicts"] += sum(r["verdict"] == "possible_conflict" for r in rows)
        overlaps = read_jsonl(settings.out_dir / "overlap" / f"{scope}.jsonl")
        if overlaps:
            lines.append("Copy overlaps (fix these first):")
            for row in overlaps:
                lines.append(
                    f"- {row['item_id']} field {row['field']}: {row['run_words']} words, "
                    f"page {row['page']}: {row['snippet']}"
                )
            totals["overlaps"] += len(overlaps)
    path = settings.out_dir / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return {"books": len(books), "scopes": len(_scopes(settings)), **totals}


def report_path(settings: Settings) -> Path:
    return settings.out_dir / "report.md"
