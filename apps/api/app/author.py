"""Authoring pipeline: section passages -> draft items -> validator -> teacher review -> live.

    python -m app.author queue  <content>                     what is waiting for a teacher
    python -m app.author status <content> --chapter <id>      what still blocks going live
    python -m app.author draft  <content> --chapter <id>      draft only the items still missing
    python -m app.author go-live <content> --chapter <id> --reviewer <id>

Nothing here approves content. Drafts are written as `status: draft`; teachers approve them
with the review sheet (`python -m app.content export-review` / `import-review`); `go-live` flips
the chapter's overlay to live only once `status` shows nothing blocking, and only for an
allowlisted reviewer.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.ask.passages import Passage, load_passages
from app.config import settings
from app.content.review import reviewer_allowlist
from app.content.schema import ItemPool, ItemRole
from app.content.validator import (
    LIVE_MIN_DIAGNOSTIC,
    LIVE_MIN_PER_ROLE,
    LIVE_MIN_PRACTICE,
    STEM_MIN_DIAGNOSTIC,
    validate_path,
)
from app.lessons.loader import load_lessons
from app.llm.draft import DraftRefused, draft_items
from app.llm.provider import LiteLLMProvider, Provider
from app.registries.loaders import ChapterSpec, load_all_curricula

DRAFT_FOLDER = "items/drafts"
ROLE_PLAN = ("explain", "apply", "transfer")


class AuthorError(RuntimeError):
    pass


def _chapter(root: Path, chapter_id: str) -> ChapterSpec:
    from app.content.validator import curricula_for

    curricula = curricula_for(root) or load_all_curricula()
    for spec in curricula.values():
        for book in spec.books:
            for chapter in book.chapters:
                if chapter.id == chapter_id:
                    return chapter
    raise AuthorError(f"unknown chapter {chapter_id!r}")


@dataclass
class ChapterStatus:
    chapter_id: str
    overlay_id: str
    live: bool = False
    blockers: list[str] = field(default_factory=list)
    awaiting_review: dict[str, int] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return not self.blockers

    def format(self) -> str:
        head = f"{self.chapter_id}: {'READY to go live' if self.ready else 'NOT ready'}"
        if self.live:
            head += " (already live)"
        lines = [head, *(f"  blocked: {b}" for b in self.blockers)]
        if self.awaiting_review:
            waiting = ", ".join(f"{k} {v}" for k, v in sorted(self.awaiting_review.items()))
            lines.append(f"  awaiting teacher review: {waiting}")
        return "\n".join(lines)


def chapter_status(root: Path, chapter_id: str) -> ChapterStatus:
    chapter = _chapter(root, chapter_id)
    report = validate_path(root)
    status = ChapterStatus(chapter_id, chapter.overlay_id)
    if report.bundle is None:
        status.blockers.append("content does not load: " + "; ".join(report.errors))
        return status
    bundle = report.bundle
    overlay = next((o for o in bundle.overlays if o.id == chapter.overlay_id), None)
    if overlay is None:
        status.blockers.append(f"no overlay {chapter.overlay_id}")
        return status
    status.live = overlay.live
    skills = set(overlay.skill_ids)
    # An already-live overlay reports its own threshold failures as errors; any other error blocks.
    status.blockers.extend(f"validation: {e}" for e in report.errors)

    lessons = load_lessons(root)
    passages = [p for p in load_passages(root) if set(p.skill_ids) & skills]
    waiting: Counter[str] = Counter()
    for skill in sorted(skills):
        mine = [i for i in bundle.items if i.primary_skill == skill]
        for pool, need in ((ItemPool.practice, LIVE_MIN_PRACTICE),):
            have = sum(i.status.value == "approved" and i.pool == pool for i in mine)
            if have < need:
                status.blockers.append(f"{skill} practice {have}/{need} approved")
        diag = sum(i.status.value == "approved" and i.pool == ItemPool.diagnostic for i in mine)
        if diag < LIVE_MIN_DIAGNOSTIC:
            status.blockers.append(f"{skill} diagnostic {diag}/{LIVE_MIN_DIAGNOSTIC} approved")
        for role in (ItemRole.explain, ItemRole.apply, ItemRole.transfer):
            have = sum(
                i.status.value == "approved" and i.pool == ItemPool.practice and i.role == role
                for i in mine
            )
            if have < LIVE_MIN_PER_ROLE:
                status.blockers.append(f"{skill} role {role.value} {have}/{LIVE_MIN_PER_ROLE}")
        lesson = next((x for x in lessons.values() if x.skill_id == skill), None)
        if lesson is None or lesson.status.value != "approved":
            status.blockers.append(f"{skill} has no approved lesson")
        if not any(p.status == "approved" for p in passages if skill in p.skill_ids):
            status.blockers.append(f"{skill} has no approved passage")
        waiting["items"] += sum(i.status.value == "draft" for i in mine)
        if lesson is not None and lesson.status.value == "draft":
            waiting["lessons"] += 1
    waiting["passages"] += sum(p.status == "draft" for p in passages)
    waiting["templates"] += sum(
        t.status.value == "draft" for t in bundle.templates if t.skill_id in skills
    )
    unchecked = [
        i.id
        for i in bundle.items
        if i.id in report.needs_teacher_check
        and i.status.value != "approved"
        and i.primary_skill in skills
    ]
    if unchecked:
        status.blockers.append(f"{len(unchecked)} item(s) need a teacher check before approval")
    if not bundle.checkpoint_forms:
        status.blockers.append("no matched checkpoint forms")
    status.awaiting_review = {k: v for k, v in waiting.items() if v}
    return status


def queue(root: Path) -> dict[str, int]:
    """Everything still in draft, across the content folder."""
    report = validate_path(root)
    if report.bundle is None:
        raise AuthorError("content does not load: " + "; ".join(report.errors))
    counts: Counter[str] = Counter()
    counts["items"] = sum(i.status.value == "draft" for i in report.bundle.items)
    counts["templates"] = sum(t.status.value == "draft" for t in report.bundle.templates)
    counts["lessons"] = sum(x.status.value == "draft" for x in load_lessons(root).values())
    counts["passages"] = sum(p.status == "draft" for p in load_passages(root))
    return dict(counts)


def _passage_text(passages: list[Passage]) -> str:
    return "\n\n".join(p.text.strip() for p in passages if p.status != "retired")


def draft_missing(root: Path, chapter_id: str, provider: Provider) -> dict[str, int]:
    """Draft only what the chapter lacks, from the passages of each skill. Returns written counts.

    Existing items of any status count as present, so running it twice does not duplicate work.
    """
    chapter = _chapter(root, chapter_id)
    report = validate_path(root)
    if report.bundle is None:
        raise AuthorError("content does not load: " + "; ".join(report.errors))
    overlay = next((o for o in report.bundle.overlays if o.id == chapter.overlay_id), None)
    if overlay is None:
        raise AuthorError(f"no overlay {chapter.overlay_id}")
    passages = load_passages(root)
    out_dir = root / DRAFT_FOLDER / chapter_id
    written: Counter[str] = Counter()
    for skill in overlay.skill_ids:
        text = _passage_text([p for p in passages if skill in p.skill_ids])
        if not text:
            written[f"{skill}: no passages"] += 0
            continue
        mine = [i for i in report.bundle.items if i.primary_skill == skill]
        practice = [i for i in mine if i.pool == ItemPool.practice]
        need_diagnostic = max(LIVE_MIN_DIAGNOSTIC, STEM_MIN_DIAGNOSTIC)  # distinct stems too
        wanted: list[tuple[str, ItemPool, int]] = [
            ("procedure", ItemPool.practice, LIVE_MIN_PRACTICE - len(practice)),
            ("procedure", ItemPool.diagnostic, need_diagnostic - sum(
                i.pool == ItemPool.diagnostic for i in mine)),
        ]  # fmt: skip
        for role in ROLE_PLAN:
            have = sum(i.role.value == role for i in practice)
            wanted.append((role, ItemPool.practice, LIVE_MIN_PER_ROLE - have))
        for role, pool, missing in wanted:
            if missing <= 0:
                continue
            result = draft_items(
                skill_id=skill,
                passages=text,
                count=max(missing, 1),
                provider=provider,
                out_dir=out_dir,
                role=role,
                pool=pool.value,
            )
            written[f"{skill} {role} {pool.value}"] += len(result.written)
    return dict(written)


def go_live(root: Path, chapter_id: str, reviewer: str) -> ChapterStatus:
    if reviewer not in reviewer_allowlist():
        raise PermissionError(f"{reviewer} is not an allowlisted reviewer")
    status = chapter_status(root, chapter_id)
    if not status.ready:
        raise AuthorError("the chapter is not ready:\n" + status.format())
    path = next(
        (
            p
            for p in sorted((root / "overlays").glob("*.yaml"))
            if (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("id") == status.overlay_id
        ),
        None,
    )
    if path is None:
        raise AuthorError(f"overlay file for {status.overlay_id} not found")
    original = path.read_text(encoding="utf-8")
    data = yaml.safe_load(original)
    data["live"] = True
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    after = validate_path(root)
    if after.errors:
        path.write_text(original, encoding="utf-8")
        raise AuthorError("going live broke validation:\n" + "\n".join(after.errors))
    status.live = True
    return status


def main(argv: list[str] | None = None, provider: Provider | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.author")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("queue", "status", "draft", "go-live"):
        cmd = sub.add_parser(name)
        cmd.add_argument("root", type=Path)
        if name != "queue":
            cmd.add_argument("--chapter", required=True)
        if name == "go-live":
            cmd.add_argument("--reviewer", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "queue":
            for kind, count in sorted(queue(args.root).items()):
                print(f"{kind}: {count} in draft")
            return 0
        if args.command == "status":
            result = chapter_status(args.root, args.chapter)
            print(result.format())
            return 0 if result.ready else 1
        if args.command == "draft":
            if settings.app_env.lower() == "production":
                print("draft is disabled when APP_ENV=production", file=sys.stderr)
                return 2
            chosen = provider
            if chosen is None:
                if not settings.llm_api_key or not settings.llm_model_strong:
                    print("draft needs LLM_API_KEY and LLM_MODEL_STRONG", file=sys.stderr)
                    return 2
                chosen = LiteLLMProvider()
            for key, count in sorted(draft_missing(args.root, args.chapter, chosen).items()):
                print(f"{key}: {count} drafted")
            return 0
        done = go_live(args.root, args.chapter, args.reviewer)
        print(done.format())
        print(f"{done.overlay_id} is now live")
        return 0
    except (AuthorError, DraftRefused, PermissionError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
