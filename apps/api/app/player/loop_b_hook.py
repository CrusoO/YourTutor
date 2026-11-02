"""Run Loop B when a practice session ends (shadow only, off unless LOOP_B_ENABLED=true).

This writes a trait profile about a learner, so it is opt-in by deployment. It never changes what a
learner sees, and it must never break a session: any failure is logged and rolled back inside a
savepoint, and the session ends as it would have without it.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.db.models import EventRow, SessionRow, SkillRow
from app.learner.bkt import BktParams
from app.learner.loop_b import HELP_SEEKING, Outcome, Versions, run_loop_b
from app.learner.loop_b_store import SqlRecordStore
from app.learner.traits import TraitPrior
from app.orchestrator.types import default_params
from app.player.ladder_log import ladder_events_from_rows, learner_events_from_ladder
from app.player.runtime import bkt_params_by_skill, load_catalog

log = logging.getLogger(__name__)

# TUNABLE-DEFAULT placeholders, to be fitted from pilot data in Loop C. Help-seeking is the share of
# answered items that were hinted first, so it lives in [0, 1].
TRAIT_PRIORS: dict[str, TraitPrior] = {
    HELP_SEEKING: TraitPrior(mu0=0.25, sigma0_sq=0.04, sigma_obs_sq=0.06, half_life_days=30.0),
}
# Bump by hand when orchestrator/policy.py changes behaviour, so a snapshot names its rules.
POLICY_VERSION = "orchestrator-v2"


def _digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def current_versions(db: Session, params: dict[str, BktParams]) -> Versions:
    """Content-derived versions: they change exactly when the graph or the parameters change."""
    graph = sorted((s.id, sorted(s.prerequisites or [])) for s in db.scalars(select(SkillRow)))
    return Versions(
        graph_version=_digest(graph),
        param_version=_digest({k: vars(v) for k, v in sorted(params.items())}),
        policy_version=POLICY_VERSION,
    )


def run_for_ended_session(
    db: Session, row: SessionRow, *, at: datetime | None = None
) -> Outcome | None:
    """Process one ended practice session. Returns None when skipped or when it failed safely."""
    if not settings.loop_b_enabled or row.type != "practice" or row.ended_at is None:
        return None
    try:
        with db.begin_nested():
            return _run(db, row, at or now_utc())
    except Exception:  # noqa: BLE001 - a shadow job must never break ending a session
        log.warning(
            "loop_b failed for session %s; session end is unaffected", row.id, exc_info=True
        )
        return None


def _run(db: Session, row: SessionRow, at: datetime) -> Outcome:
    db.flush()  # the event that ended the session is not in the database until now
    catalog = load_catalog(db, allow_draft=settings.allow_draft_content)
    by_id = {item.id: item for item in catalog}
    params = bkt_params_by_skill(db)
    for item in catalog:
        params.setdefault(item.primary_skill, default_params())

    rows = db.execute(
        select(EventRow, SessionRow.type)
        .join(SessionRow, EventRow.session_id == SessionRow.id)
        .where(SessionRow.student_id == row.student_id)
        .order_by(EventRow.created_at, EventRow.id)
    ).all()
    pairs = [(event, session_type) for event, session_type in rows]
    mine = [(event, session_type) for event, session_type in pairs if event.session_id == row.id]

    watermark = db.scalar(
        select(func.count()).select_from(EventRow).where(EventRow.session_id == row.id)
    )
    return run_loop_b(
        SqlRecordStore(db),
        learner_id=str(row.student_id),
        session_id=str(row.id),
        watermark=int(watermark or 0),
        all_events=learner_events_from_ladder(ladder_events_from_rows(pairs, by_id)),
        session_events=learner_events_from_ladder(ladder_events_from_rows(mine, by_id)),
        params_by_skill=params,
        trait_priors=TRAIT_PRIORS,
        versions=current_versions(db, params),
        at=at,
    )
