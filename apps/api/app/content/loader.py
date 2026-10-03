from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.content.schema import ContentBundle
from app.content.validator import ValidationReport, load_bundle, validate_bundle, _persist_hash_resets
from app.db.models import (
    Base,
    CheckpointFormRow,
    GlossaryTermRow,
    ItemRow,
    MisconceptionRow,
    OverlayRow,
    SkillRow,
)
from app.db.session import make_engine, session_factory


class LoadError(RuntimeError):
    pass


def load_path(
    root: Path,
    *,
    database_url: str | None = None,
    include_e2e_mini: bool = False,
) -> ValidationReport:
    from app.content.bundle_merge import load_content_bundle
    try:
        bundle = load_content_bundle(root) if include_e2e_mini else load_bundle(root)
    except Exception as exc:
        raise LoadError(str(exc)) from exc
    report = validate_bundle(bundle)
    _persist_hash_resets(root, report)
    if not report.ok or report.bundle is None:
        raise LoadError("validation failed:\n" + "\n".join(report.errors))
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    factory = session_factory(database_url)
    with factory() as session:
        _upsert(session, report.bundle)
        session.commit()
    return report


def _upsert(session: Session, bundle: ContentBundle) -> None:
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
    if keep_items:
        session.query(ItemRow).filter(~ItemRow.id.in_(keep_items)).delete(synchronize_session=False)
    else:
        session.query(ItemRow).delete()
    for item in bundle.items:
        session.merge(
            ItemRow(
                id=item.id,
                skill_ids=item.skill_ids,
                primary_skill=item.primary_skill,
                difficulty=item.difficulty,
                type=item.type.value,
                pool=item.pool.value,
                stem=item.stem.as_dict(),
                verify=item.verify if isinstance(item.verify, str) else (
                    item.verify.model_dump() if item.verify else None
                ),
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
    if keep_skills:
        session.query(SkillRow).filter(~SkillRow.id.in_(keep_skills)).delete(
            synchronize_session=False
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
                board=overlay.board,
                grade=overlay.grade,
                chapter=overlay.chapter,
                skill_ids=overlay.skill_ids,
                live=overlay.live,
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
