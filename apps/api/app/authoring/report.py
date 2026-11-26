"""Progress report: what is drafted per class, subject, chapter and topic, against the target."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.authoring.files import draft_files, drafts_root, read_draft
from app.authoring.lint import ITEMS_PER_TOPIC
from app.authoring.syllabus import all_maps


@dataclass
class TopicRow:
    grade: int
    subject: str
    chapter: str
    topic: str
    kind: str
    needs_draft: bool
    items: int = 0
    low_confidence: int = 0
    diagrams: int = 0


@dataclass
class Report:
    rows: list[TopicRow] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        wanted = [r for r in self.rows if r.needs_draft]
        return {
            "target_per_topic": ITEMS_PER_TOPIC,
            "topics_to_draft": len(wanted),
            "topics_with_drafts": sum(1 for r in wanted if r.items),
            "topics_complete": sum(1 for r in wanted if r.items >= ITEMS_PER_TOPIC),
            "items": sum(r.items for r in self.rows),
            "low_confidence": sum(r.low_confidence for r in self.rows),
            "topics_without_drafts": [
                f"{r.grade}/{r.subject}/{r.chapter}/{r.topic}" for r in wanted if not r.items
            ],
            "unreadable_files": self.unreadable,
            "draft_keys_not_in_map": self.unknown,
            "rows": [r.__dict__ for r in self.rows],
        }

    def to_text(self) -> str:
        lines: list[str] = []
        by_group: dict[tuple[int, str], list[TopicRow]] = {}
        for r in self.rows:
            by_group.setdefault((r.grade, r.subject), []).append(r)
        for (grade, subject), rows in by_group.items():
            wanted = [r for r in rows if r.needs_draft]
            lines.append(
                f"class {grade} {subject}: {sum(r.items for r in rows)} items, "
                f"{sum(1 for r in wanted if r.items >= ITEMS_PER_TOPIC)}/{len(wanted)} topics at "
                f"target {ITEMS_PER_TOPIC}, {sum(r.low_confidence for r in rows)} low confidence"
            )
            chapters = Counter(r.chapter for r in rows)
            for chapter in chapters:
                inside = [r for r in rows if r.chapter == chapter]
                total = sum(r.items for r in inside)
                lines.append(f"  {chapter}: {total} items")
                for r in inside:
                    if not r.needs_draft:
                        lines.append(f"    {r.topic}: not drafted (computed topic)")
                    else:
                        extra = f", {r.low_confidence} low" if r.low_confidence else ""
                        lines.append(f"    {r.topic}: {r.items}/{ITEMS_PER_TOPIC}{extra}")
        summary = self.to_json()
        lines.append(
            f"total: {summary['items']} items, {summary['topics_complete']}/"
            f"{summary['topics_to_draft']} topics complete, {summary['low_confidence']} low "
            f"confidence, {len(summary['topics_without_drafts'])} topics without drafts"
        )
        for name in self.unreadable:
            lines.append(f"unreadable draft file: {name}")
        for name in self.unknown:
            lines.append(f"draft key not in the syllabus map: {name}")
        return "\n".join(lines)


def build_report(content_root: Path) -> Report:
    report = Report()
    index: dict[tuple[int, str, str, str], TopicRow] = {}
    for smap in all_maps(content_root):
        for chapter in smap.chapters:
            for topic in chapter.topics:
                needs = not (smap.class_ == 10 and topic.kind == "computed")
                row = TopicRow(smap.class_, smap.subject, chapter.key, topic.key, topic.kind, needs)
                report.rows.append(row)
                index[(smap.class_, smap.subject, chapter.key, topic.key)] = row
    for path in draft_files(drafts_root(content_root)):
        draft, _ = read_draft(path)
        if draft is None:
            report.unreadable.append(path.as_posix())
            continue
        for item in draft.items:
            found = index.get((draft.class_, draft.subject, draft.chapter, item.topic))
            if found is None:
                report.unknown.append(
                    f"{draft.class_}/{draft.subject}/{draft.chapter}/{item.topic}"
                )
                continue
            found.items += 1
            found.low_confidence += item.confidence == "low"
            found.diagrams += bool(item.diagram)
    return report
