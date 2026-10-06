from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.content.gate import RETIRED_STATUS
from app.content.schema import ContentBundle
from app.content.validator import (
    ValidationReport,
    _persist_hash_resets,
    curricula_for,
    load_bundle,
    validate_bundle,
)
from app.db.models import (
    Base,
    CheckpointFormRow,
    EventRow,
    GlossaryTermRow,
    ItemRow,
    MasteryRow,
    MisconceptionHitRow,
    MisconceptionRow,
    OverlayRow,
    ReviewCardRow,
    SkillRow,
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

    if not root.is_dir():
        raise LoadError(f"content root {root} does not exist or is not a folder")
    try:
        bundle = load_content_bundle(root) if include_e2e_mini else load_bundle(root)
    except Exception as exc:
        raise LoadError(str(exc)) from exc
    if not bundle.skills or not bundle.items:
        # An empty bundle would retire (or, in dev, hard-delete) everything already loaded.
        raise LoadError(f"content root {root} has no skills or items; refusing to load")
    report = validate_bundle(bundle, curricula_for(root))
    _persist_hash_resets(root, report)
    if not report.ok or report.bundle is None:
        raise LoadError("validation failed:\n" + "\n".join(report.errors))
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    factory = session_factory(database_url)
    with factory() as session:
        try:
            _upsert(session, report.bundle, prune=prune)
            seed_g0_registry(session)  # registry YAML is the source of truth
            session.commit()
        except PruneBlockedError:
            session.rollback()
            raise
    return report


def _upsert(session: Session, bundle: ContentBundle, *, prune: bool) -> None:
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
                status=item.status.value,
                reviewed_by=item.reviewed_by,
                content_hash=item.content_hash,
                template_id=item.template_id,
                generator_version=item.generator_version,
                template_hash=item.template_hash,
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
