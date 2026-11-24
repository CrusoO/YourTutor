"""Template-level approval for the reviewer desk (REVIEW_TEMPLATE_APPROVAL_ENABLED). Records only.

The factory makes many questions (items) from one template. With this switched on a reviewer
approves a template by approving a few SAMPLE questions from it; nothing new is stored. Everything
here is worked out from the existing `content_reviews` rows:

* A TEMPLATE VERSION is (template_id, template_hash, generator_version) over the DRAFT items that
  carry it. A change to the hash or the generator makes a new version, so earlier approvals do not
  count (they are keyed to the samples' content hashes anyway).
* SAMPLES, the same for every reviewer: sort the version's items by (difficulty, id) and take the
  easiest, the middle (index n // 2) and the hardest; with fewer than three items take them all. No
  randomness, no clock.
* A reviewer has APPROVED a version when they hold a standing approve on ALL its samples at their
  current content hashes (a skip does not count, a withdrawn decision is void).
* REQUIRED approvals: `REVIEW_TEMPLATE_APPROVALS_REQUIRED` (default 1), raised to 2 for a template
  id that starts with one of `REVIEW_TEMPLATE_DOUBLE_REVIEW_PREFIXES` (laws and facts: physics,
  chemistry, biology, health) and for a deterministic `REVIEW_TEMPLATE_DOUBLE_REVIEW_PERCENT` share
  of the rest: int(sha256(template_hash)[:8], 16) % 100 < percent.
* BLOCK AND ESCALATE: a standing fix or reject by anyone on a sample blocks the version. Its items
  all enter the reviewers' `todo` queue for individual (item-level) review until the template
  changes and becomes a new version.
* STATE: in_review, ready (enough approvals and nothing blocking), blocked (a block stands and the
  samples are all its items), escalated (a block stands and there are more items than samples).

Items with no `template_id` are not covered and stay item-level. This module never changes what a
learner is served and never touches an item's `status`: turning ready templates into approved
content is a later, owner-reviewed step.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content_review import service, snapshot
from app.db.models import ContentReviewRow

SAMPLE_COUNT = 3
STATES = ("in_review", "ready", "blocked", "escalated")


def template_mode() -> bool:
    """Template approval applies only with the desk on as well."""
    return settings.reviewer_desk_enabled and settings.review_template_approval_enabled


def sample_ids(items: Iterable[Item]) -> list[str]:
    """The deterministic samples: easiest, middle, hardest by (difficulty, id); all when fewer
    than three."""
    ordered = sorted(items, key=lambda i: (i.difficulty, i.id))
    if len(ordered) <= SAMPLE_COUNT:
        return [i.id for i in ordered]
    return [ordered[0].id, ordered[len(ordered) // 2].id, ordered[-1].id]


def _prefixes() -> list[str]:
    return [
        p.strip() for p in settings.review_template_double_review_prefixes.split(",") if p.strip()
    ]


def needs_double_review(template_id: str, template_hash: str) -> bool:
    """Family rule (laws and facts) or the deterministic share of the others."""
    for prefix in _prefixes():
        if template_id == prefix or template_id.startswith(prefix + "."):
            return True
    percent = max(0, min(100, settings.review_template_double_review_percent))
    bucket = int(hashlib.sha256(template_hash.encode("utf-8")).hexdigest()[:8], 16) % 100
    return bucket < percent


def required_approvals(template_id: str, template_hash: str) -> int:
    base = max(1, settings.review_template_approvals_required)
    return max(base, 2) if needs_double_review(template_id, template_hash) else base


@dataclass(frozen=True)
class TemplateVersion:
    template_id: str
    template_hash: str
    generator_version: str
    item_ids: tuple[str, ...]  # draft items, in id order
    samples: tuple[tuple[str, str], ...]  # (item id, content hash), easiest to hardest
    required: int
    chapter_id: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.template_id, self.template_hash, self.generator_version)

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(i for i, _ in self.samples)


def build_versions(data: snapshot.ReviewData) -> list[TemplateVersion]:
    """Every template version that has draft items, in key order. Hashes only the samples."""
    groups: dict[tuple[str, str, str], list[Item]] = {}
    for item in data.items:
        if item.template_id and service.is_draft(item):
            key = (item.template_id, item.template_hash or "", item.generator_version or "")
            groups.setdefault(key, []).append(item)
    out = []
    for key in sorted(groups):
        items = sorted(groups[key], key=lambda i: i.id)
        by_id = {i.id: i for i in items}
        picked = sample_ids(items)
        out.append(
            TemplateVersion(
                template_id=key[0],
                template_hash=key[1],
                generator_version=key[2],
                item_ids=tuple(i.id for i in items),
                samples=tuple((s, item_content_hash(by_id[s])) for s in picked),
                required=required_approvals(key[0], key[1]),
                chapter_id=data.item_chapter.get(items[0].id, snapshot.UNMAPPED_ID),
            )
        )
    return out


def sample_info(versions: Iterable[TemplateVersion]) -> dict[str, dict[str, Any]]:
    """Per sample item id: which sample it is. Safe to show a reviewer (no votes in it)."""
    info: dict[str, dict[str, Any]] = {}
    for v in versions:
        for n, sample in enumerate(v.sample_ids, start=1):
            info[sample] = {
                "template_id": v.template_id,
                "sample_index": n,
                "sample_count": len(v.samples),
                "questions": len(v.item_ids),
            }
    return info


@dataclass
class VersionStatus:
    version: TemplateVersion
    approvers: set[uuid.UUID] = field(default_factory=set)
    blockers: set[uuid.UUID] = field(default_factory=set)
    # reviewer -> number of samples they have a standing approve on (admin detail only)
    approved_samples: dict[uuid.UUID, int] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return bool(self.blockers)

    @property
    def state(self) -> str:
        v = self.version
        if self.blocked:
            return "escalated" if len(v.item_ids) > len(v.samples) else "blocked"
        return "ready" if len(self.approvers) >= v.required else "in_review"


def _status(
    version: TemplateVersion, reviews: dict[tuple[str, str], list[ContentReviewRow]]
) -> VersionStatus:
    status = VersionStatus(version)
    counts: dict[uuid.UUID, int] = {}
    for pair in version.samples:
        for reviewer, row in service.standing(reviews.get(pair, [])).items():
            if row.decision == "approve":
                counts[reviewer] = counts.get(reviewer, 0) + 1
            elif row.decision in ("reject", "fix"):
                status.blockers.add(reviewer)
    status.approved_samples = counts
    status.approvers = {r for r, n in counts.items() if n == len(version.samples)}
    return status


@dataclass
class Analysis:
    """Versions, their states and the reviews of every item that may be in a queue."""

    versions: list[TemplateVersion]
    statuses: dict[tuple[str, str, str], VersionStatus]
    reviews: dict[tuple[str, str], list[ContentReviewRow]]
    candidates: dict[
        str, tuple[Item, str]
    ]  # item id -> (item, content hash) that can be in a queue
    version_of: dict[str, tuple[str, str, str]]  # item id -> version key

    def todo_ids(self, me: uuid.UUID) -> set[str]:
        """Items `me` still owes: no standing decision of theirs, among the drafts that are not
        covered by a template, the samples of every version and all items of a blocked version."""
        out = set()
        for item_id, (_, digest) in self.candidates.items():
            rows = self.reviews[(item_id, digest)]
            if not service.has_decided(rows, me):
                out.add(item_id)
        return out

    def templates_left(self, todo: set[str], chapter_of: dict[str, str]) -> dict[str, int]:
        """chapter id -> number of template versions with an item of that chapter in `todo`."""
        seen = {
            (chapter_of.get(item_id, snapshot.UNMAPPED_ID), key)
            for item_id in todo
            if (key := self.version_of.get(item_id)) is not None
        }
        counts: dict[str, int] = {}
        for chapter, _ in seen:
            counts[chapter] = counts.get(chapter, 0) + 1
        return counts


def analyse(db: Session, data: snapshot.ReviewData) -> Analysis:
    versions = build_versions(data)
    version_of: dict[str, tuple[str, str, str]] = {}
    for v in versions:
        for item_id in v.item_ids:
            version_of[item_id] = v.key
    drafts = {i.id: i for i in data.items if service.is_draft(i)}
    sample_pairs = {pair for v in versions for pair in v.samples}
    reviews = service.reviews_for_items(db, sorted(sample_pairs))
    statuses = {v.key: _status(v, reviews) for v in versions}
    samples = dict(sample_pairs)
    candidates: dict[str, tuple[Item, str]] = {}
    for item_id, item in drafts.items():
        key = version_of.get(item_id)
        if key is None or statuses[key].blocked:
            # not covered by a template (item level), or its template is blocked (escalated)
            candidates[item_id] = (item, item_content_hash(item))
        elif item_id in samples:
            candidates[item_id] = (item, samples[item_id])
    # the sample rows are already read; fetch the rest (item-level and escalated items)
    missing = [(i, h) for i, (_, h) in candidates.items() if (i, h) not in reviews]
    reviews.update(service.reviews_for_items(db, missing))
    return Analysis(versions, statuses, reviews, candidates, version_of)


def summary(analysis: Analysis, data: snapshot.ReviewData) -> dict[str, Any]:
    """Admin view: counts by state in total and per chapter, and the blocked or escalated
    versions with their ids. No reviewer identities."""
    totals = {s: 0 for s in STATES}
    per_chapter: dict[str, dict[str, int]] = {}
    flagged = []
    for status in analysis.statuses.values():
        v = status.version
        totals[status.state] += 1
        chapter = per_chapter.setdefault(v.chapter_id, {s: 0 for s in STATES})
        chapter[status.state] += 1
        if status.blocked:
            flagged.append(
                {
                    "template_id": v.template_id,
                    "template_hash": v.template_hash,
                    "generator_version": v.generator_version,
                    "state": status.state,
                    "chapter": v.chapter_id,
                    "questions": len(v.item_ids),
                    "samples": list(v.sample_ids),
                }
            )
    chapters = []
    for chapter_id in sorted(per_chapter):
        found = data.chapters.get(chapter_id)
        chapters.append(
            {
                "chapter": chapter_id,
                "title": found.title if found is not None else chapter_id,
                **per_chapter[chapter_id],
                "total": sum(per_chapter[chapter_id].values()),
            }
        )
    return {
        "totals": {**totals, "total": sum(totals.values())},
        "chapters": chapters,
        "blocked": flagged,
    }


def detail(analysis: Analysis, template_id: str) -> list[dict[str, Any]]:
    """Admin view of every version of one template: samples and each reviewer's state, by
    pseudonymous label only."""
    out = []
    for status in analysis.statuses.values():
        v = status.version
        if v.template_id != template_id:
            continue
        reviewers = sorted(
            set(status.approved_samples) | status.blockers, key=service.reviewer_label
        )
        out.append(
            {
                "template_id": v.template_id,
                "template_hash": v.template_hash,
                "generator_version": v.generator_version,
                "state": status.state,
                "chapter": v.chapter_id,
                "questions": len(v.item_ids),
                "samples": [{"item_id": i, "content_hash": h} for i, h in v.samples],
                "approvals": len(status.approvers),
                "approvals_needed": v.required,
                "double_review": needs_double_review(v.template_id, v.template_hash),
                "reviewers": [
                    {
                        "label": service.reviewer_label(r),
                        "approved_samples": status.approved_samples.get(r, 0),
                        "blocking": r in status.blockers,
                    }
                    for r in reviewers
                ],
            }
        )
    return out


def apply_to_groups(
    analysis: Analysis, data: snapshot.ReviewData, groups: list[dict[str, Any]], me: uuid.UUID
) -> list[dict[str, Any]]:
    """Template mode for the chapter picker: `pending` becomes the items `me` still owes (samples
    and escalated items) and `templates_pending` the question types behind them. Reads only `me`'s
    own decisions plus the block state that escalation needs, never a vote."""
    todo = analysis.todo_ids(me)
    items_left: dict[str, int] = {}
    for item_id in todo:
        chapter = data.item_chapter.get(item_id, snapshot.UNMAPPED_ID)
        items_left[chapter] = items_left.get(chapter, 0) + 1
    types_left = analysis.templates_left(todo, data.item_chapter)
    out = []
    for group in groups:
        chapter = group["chapter"]
        out.append(
            {
                **group,
                "pending": items_left.get(chapter, 0),
                "templates_pending": types_left.get(chapter, 0),
            }
        )
    return out
