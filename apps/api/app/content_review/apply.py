"""`python -m app.content apply-reviews`: write review approvals from the database into the YAML.

The approval writing is the existing `_approve_items` in `app.content.review` (validates the whole
bundle first and refuses an item that would break it); this only decides WHICH items qualify.
`reviewed_by` records the approving reviewers' labels, sorted and joined with a comma.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.content.review import ImportReport, _approve_items
from app.content.signatures import item_content_hash
from app.content.validator import validate_path
from app.content_review import service


@dataclass
class ApplyReport:
    approved: list[str] = field(default_factory=list)
    waiting: list[str] = field(default_factory=list)  # drafts with some approvals, not enough
    blocked: list[str] = field(default_factory=list)  # a reject or fix stands
    refused: list[str] = field(default_factory=list)  # failed validation when written


def apply_reviews(db: Session, root: Path) -> ApplyReport:
    report = validate_path(root)
    if report.bundle is None:
        raise RuntimeError("cannot apply: " + "; ".join(report.errors))
    out = ApplyReport()
    groups: dict[str, list] = {}
    for item in report.bundle.items:
        if not service.is_draft(item):
            continue
        rows = service.reviews_for(db, item.id, item_content_hash(item))
        counted = service.tally(rows)
        if counted.blocked:
            out.blocked.append(item.id)
        elif counted.ready:
            who = sorted({r.reviewer_label for r in rows if r.decision == "approve"})
            groups.setdefault(", ".join(who), []).append(item)
        elif counted.approvals:
            out.waiting.append(item.id)
    for reviewers, items in groups.items():
        written = ImportReport()
        _approve_items(report.bundle, items, root, reviewers, written)
        out.approved.extend(written.approved)
        out.refused.extend(written.refused)
    return out
