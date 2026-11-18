from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.config import settings
from app.content.gate import RETIRED_STATUS
from app.content.schema import ContentBundle
from app.content.validator import (
    ValidationReport,
    _persist_hash_resets,
    _validate_with_factory,
    curricula_for,
    load_bundle,
)
from app.db.models import (
    Base,
    CheckpointFormRow,
    EventRow,
    GlossaryTermRow,
    ItemRow,
    LessonRow,
    MasteryRow,
    MisconceptionHitRow,
    MisconceptionRow,
    OverlayRow,
    ReviewCardRow,
    SceneRow,
    SkillRow,
    WidgetRow,
)
from app.db.session import make_engine, session_factory
from app.registries.seed_db import seed_g0_registry


class LoadError(RuntimeError):
    pass


class PruneBlockedError(LoadError):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("prune blocked: " + "; ".join(reasons))


def load_path(
    root: Path,
    *,
    database_url: str | None = None,
    include_e2e_mini: bool = False,
    prune: bool = False,
) -> ValidationReport:
    from app.content.bundle_merge import load_content_bundle
    from app.lessons.loader import lesson_errors  # lazy: lessons import app.content.schema

    if not root.is_dir():
        raise LoadError(f"content root {root} does not exist or is not a folder")
    from app.content.approval import reset_stale_approvals

    stale_approvals = reset_stale_approvals(root)
    try:
        bundle = load_content_bundle(root) if include_e2e_mini else load_bundle(root)
    except Exception as exc:
        raise LoadError(str(exc)) from exc
    empty = not bundle.skills or not bundle.items
    if empty and _database_has_content(database_url):
        # An empty bundle would retire (or, in dev, hard-delete) everything already loaded.
        raise LoadError(f"content root {root} has no skills or items; refusing to load")
    report = _validate_with_factory(root, bundle)
    report.warnings.extend(stale_approvals)
    _persist_hash_resets(root, report)
    from app.content.sources import rights_errors

    report.errors.extend(rights_errors(root, bundle.items))
    from app.lessons.sources import approved_source_ids, source_errors

    report.errors.extend(source_errors(root))
    report.errors.extend(
        lesson_errors(
            root,
            {skill.id for skill in bundle.skills},
            sources=approved_source_ids(root),
            item_skills={item.id: item.primary_skill for item in bundle.items},
        )
    )
    from app.lessons.loader import live_lesson_errors, load_lessons

    if not any(e.startswith("lesson ") for e in report.errors):
        report.errors.extend(live_lesson_errors(load_lessons(root), bundle.overlays))
    from app.ask.load import validate_passages
    from app.lessons.sources import approved_source_ids as _approved
    from app.registries.loaders import load_all_curricula

    report.errors.extend(
        validate_passages(
            root,
            curricula_for(root) or load_all_curricula(),
            {skill.id for skill in bundle.skills},
            _approved(root),
        )
    )
    from app.content.copy import copy_errors  # lazy: copy imports the orchestrator's variant table

    report.errors.extend(copy_errors(root))
    backing, suspended_ids = _factory_backing(root, report)
    if not report.ok or report.bundle is None:
        raise LoadError("validation failed:\n" + "\n".join(report.errors))
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    factory = session_factory(database_url)
    with factory() as session:
        try:
            _upsert(session, report.bundle, prune=prune, backing=backing)
            _suspend_from_ledger(session, suspended_ids)
            _upsert_lessons(session, root)
            from app.ask.load import upsert_passages

            upsert_passages(session, root, curricula_for(root) or load_all_curricula())
            seed_g0_registry(session)  # registry YAML is the source of truth
            session.commit()
        except PruneBlockedError:
            session.rollback()
            raise
    return report


def _factory_backing(
    root: Path, report: ValidationReport
) -> tuple[dict[str, tuple[str | None, dict | None]], set[str]]:
    """Per item: (tier to store, verification record to keep). A hand-written tier A is ignored
    unless an intact record in the stamp ledger backs it (warning says so). Also returns the item
    ids the ledger records as suspended."""
    from app.content.factory_roots import read_ledgers
    from app.content.signatures import item_content_hash
    from app.content.verification import effective_tier

    ledgers = read_ledgers(root)
    problems = ledgers.problems
    for p in problems:
        message = f"factory ledger: {p}"
        if message not in report.errors:  # validate already reported it
            report.errors.append(message)
    stamped = ledgers.stamped
    out: dict[str, tuple[str | None, dict | None]] = {}
    if report.bundle is None:
        return out, set()
    for item in report.bundle.items:
        record = item.verification.as_record() if item.verification else None
        tier, warning = effective_tier(
            item.tier.value if item.tier else None,
            record,
            item_hash=item_content_hash(item),
            stamped_hashes=stamped,
            reviewed_by=item.reviewed_by,
        )
        if warning:
            report.warnings.append(
                f"{item.id}: tier {item.tier.value if item.tier else ''} ignored ({warning})"
            )
        out[item.id] = (tier, record if tier in ("A", "B") and record else None)
    return out, ledgers.suspended


def _suspend_from_ledger(session: Session, item_ids: set[str]) -> None:
    from datetime import UTC, datetime

    session.flush()  # the rows merged just now must be visible to the select below
    for row in (
        session.scalars(select(ItemRow).where(ItemRow.id.in_(item_ids))).all() if item_ids else []
    ):
        if row.suspended_at is None:
            row.suspended_at = datetime.now(UTC)
            row.suspension_reason = row.suspension_reason or "suspended in the factory ledger"


def _database_has_content(database_url: str | None) -> bool:
    """True when skills or items are already loaded (so an empty bundle must not replace them).

    A fresh database has nothing to lose, so an empty content root (the production skeleton
    before the factory stamps anything) loads as a no-op that still seeds the registries.
    """
    engine = make_engine(database_url)
    try:
        names = set(inspect(engine).get_table_names())
        if not {SkillRow.__tablename__, ItemRow.__tablename__} <= names:
            return False
        with Session(engine) as session:
            skills = session.scalar(select(func.count()).select_from(SkillRow)) or 0
            items = session.scalar(select(func.count()).select_from(ItemRow)) or 0
    finally:
        engine.dispose()
    return bool(skills or items)


def _upsert_lessons(session: Session, root: Path) -> None:
    """Replace the lesson, scene and widget rows with what `<root>/lessons` holds."""
    import json

    from app.lessons.budget import scene_bytes, scene_duration_seconds, scene_kb_per_minute
    from app.lessons.loader import load_lessons

    lessons = load_lessons(root)
    session.query(WidgetRow).delete()
    session.query(SceneRow).delete()
    session.query(LessonRow).delete()
    for lesson in lessons.values():
        session.add(
            LessonRow(
                id=lesson.id,
                skill_id=lesson.skill_id,
                title=lesson.title.as_dict(),
                source_ref=lesson.source_ref,
                status=lesson.status.value,
                beats=json.loads(lesson.model_dump_json(by_alias=True, exclude_none=True))["beats"],
            )
        )
    session.flush()
    for lesson in lessons.values():
        for scene in lesson.scenes():
            session.add(
                SceneRow(
                    id=f"{lesson.id}:{scene.id}",
                    lesson_id=lesson.id,
                    skill_id=scene.skill_id,
                    source_ref=scene.source_ref,
                    body=json.loads(scene.model_dump_json(by_alias=True, exclude_none=True)),
                    size_bytes=scene_bytes(scene),
                    duration_s=scene_duration_seconds(scene),
                    kb_per_minute=scene_kb_per_minute(scene),
                )
            )
        for widget in lesson.widgets():
            session.add(
                WidgetRow(
                    id=f"{lesson.id}:{widget.widget_id}",
                    lesson_id=lesson.id,
                    type=widget.type,
                    body=json.loads(widget.model_dump_json(by_alias=True, exclude_none=True)),
                )
            )


def _upsert(
    session: Session,
    bundle: ContentBundle,
    *,
    prune: bool,
    backing: dict[str, tuple[str | None, dict | None]] | None = None,
) -> None:
    from app.content.signatures import item_content_hash
    from app.content.verification import effective_tier

    backing = backing or {}
    session.query(GlossaryTermRow).delete()
    keep_skills = {skill.id for skill in bundle.skills}
    for skill in bundle.skills:
        session.merge(
            SkillRow(
                id=skill.id,
                title=skill.title.as_dict(),
                grade_band=skill.grade_band,
                subject=skill.subject,
                prerequisites=skill.prerequisites,
                related=skill.related,
                misconceptions=skill.misconceptions,
                bkt=skill.bkt.model_dump(),
                status=skill.status.value,
            )
        )
    keep_items = {item.id for item in bundle.items}
    for item in bundle.items:
        # No ledger passed (a direct _upsert call): nothing can back a tier, so a hand-written A is
        # dropped here too.
        tier_value, record = backing.get(item.id) or effective_tier(
            item.tier.value if item.tier else None,
            item.verification.as_record() if item.verification else None,
            item_hash=item_content_hash(item),
            stamped_hashes=set(),
            reviewed_by=item.reviewed_by,
        )[:1] + (None,)
        session.merge(
            ItemRow(
                id=item.id,
                skill_ids=item.skill_ids,
                primary_skill=item.primary_skill,
                difficulty=item.difficulty,
                type=item.type.value,
                pool=item.pool.value,
                role=item.role.value,
                stem=item.stem.as_dict(),
                verify=item.verify
                if isinstance(item.verify, str)
                else (item.verify.model_dump() if item.verify else None),
                options=[o.model_dump(by_alias=True) for o in item.options],
                answer=item.answer.model_dump(),
                solution_steps=[s.as_dict() for s in item.solution_steps],
                hints=[h.model_dump(by_alias=True) for h in item.hints],
                prediction_prompt=item.prediction_prompt.as_dict(),
                misconception_rules=[r.model_dump() for r in item.misconception_rules],
                slip_patterns=[p.model_dump(exclude_none=True) for p in item.slip_patterns],
                prereq_signatures=[p.model_dump() for p in item.prereq_signatures],
                intermediate_values=list(item.intermediate_values),
                min_plausible_ms=item.min_plausible_ms,
                step_hints=[s.as_dict() for s in item.step_hints],
                hint_restate=item.hint_restate.as_dict() if item.hint_restate else None,
                status=item.status.value,
                reviewed_by=item.reviewed_by,
                content_hash=item.content_hash,
                template_id=item.template_id,
                generator_version=item.generator_version,
                template_hash=item.template_hash,
                tier=tier_value,
                provenance=item.provenance.model_dump() if item.provenance else None,
                verification=record,
                certificate_hash=record.get("certificate_hash") if record else None,
            )
        )
    for mc in bundle.misconceptions:
        session.merge(
            MisconceptionRow(
                id=mc.id,
                title=mc.title.as_dict(),
                explanation=mc.explanation.as_dict(),
                remedial_skill=mc.remedial_skill,
                status=mc.status.value,
            )
        )
    for overlay in bundle.overlays:
        session.merge(
            OverlayRow(
                id=overlay.id,
                curriculum_id=overlay.curriculum_id,
                grade=overlay.grade,
                chapter=overlay.chapter,
                skill_ids=overlay.skill_ids,
                live=overlay.live,
                section_map=overlay.section_map,
            )
        )
    for forms in bundle.checkpoint_forms:
        session.merge(
            CheckpointFormRow(
                id=forms.id,
                checkpoint_id=forms.checkpoint_id,
                form_a=forms.form_a,
                form_b=forms.form_b,
                match_map=forms.match_map,
            )
        )
    for glossary in bundle.glossaries:
        for term, translation in glossary.terms.items():
            session.add(
                GlossaryTermRow(
                    language=glossary.language,
                    term=term,
                    translation=translation,
                )
            )

    orphan_skill_ids = _orphan_skill_ids(session, keep_skills)
    orphan_item_ids = _orphan_item_ids(session, keep_items)
    hard_delete = settings.allow_draft_content or prune
    if hard_delete:
        if prune:
            reasons = _prune_block_reasons(session, orphan_skill_ids, orphan_item_ids)
            if reasons:
                raise PruneBlockedError(reasons)
        _hard_delete_orphans(session, orphan_skill_ids, orphan_item_ids)
    else:
        _retire_orphans(session, orphan_skill_ids, orphan_item_ids)


def _orphan_skill_ids(session: Session, keep_skills: set[str]) -> set[str]:
    rows = session.scalars(select(SkillRow.id)).all()
    if not keep_skills:
        return set(rows)
    return {sid for sid in rows if sid not in keep_skills}


def _orphan_item_ids(session: Session, keep_items: set[str]) -> set[str]:
    rows = session.scalars(select(ItemRow.id)).all()
    if not keep_items:
        return set(rows)
    return {iid for iid in rows if iid not in keep_items}


def _retire_orphans(session: Session, skill_ids: set[str], item_ids: set[str]) -> None:
    if item_ids:
        session.query(ItemRow).filter(ItemRow.id.in_(item_ids)).update(
            {ItemRow.status: RETIRED_STATUS},
            synchronize_session=False,
        )
    if skill_ids:
        session.query(SkillRow).filter(SkillRow.id.in_(skill_ids)).update(
            {SkillRow.status: RETIRED_STATUS},
            synchronize_session=False,
        )


def _hard_delete_orphans(session: Session, skill_ids: set[str], item_ids: set[str]) -> None:
    if item_ids:
        session.query(ItemRow).filter(ItemRow.id.in_(item_ids)).delete(synchronize_session=False)
    if skill_ids:
        session.query(SkillRow).filter(SkillRow.id.in_(skill_ids)).delete(synchronize_session=False)


def _prune_block_reasons(
    session: Session,
    skill_ids: set[str],
    item_ids: set[str],
) -> list[str]:
    reasons: list[str] = []
    if skill_ids:
        mastery = session.scalar(
            select(func.count()).select_from(MasteryRow).where(MasteryRow.skill_id.in_(skill_ids))
        )
        if mastery:
            reasons.append(f"mastery references {mastery} retired skill(s)")
        cards = session.scalar(
            select(func.count())
            .select_from(ReviewCardRow)
            .where(ReviewCardRow.skill_id.in_(skill_ids))
        )
        if cards:
            reasons.append(f"review_cards references {cards} retired skill(s)")
    if item_ids:
        events = session.scalar(
            select(func.count()).select_from(EventRow).where(EventRow.item_id.in_(item_ids))
        )
        if events:
            reasons.append(f"events references {events} retired item(s)")
        hits = session.scalar(
            select(func.count())
            .select_from(MisconceptionHitRow)
            .where(MisconceptionHitRow.item_id.in_(item_ids))
        )
        if hits:
            reasons.append(f"misconception_hits references {hits} retired item(s)")
    return reasons
