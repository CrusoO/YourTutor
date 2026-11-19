"""The one call the player makes after a wrong answer: weigh the causes and say what to do next.

Reads the same authored signatures as the diagnosis engine (it calls `find_causes`), so nothing is
matched twice and the two can never disagree about what an answer looks like.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.learner.reason.config import DEFAULT_CONFIG, ReasonConfig
from app.learner.reason.posterior import (
    Confidence,
    Posterior,
    ReasonView,
    cause_id,
    likelihoods,
    update,
    view,
)
from app.learner.types import LearnerState
from app.orchestrator.diagnosis import find_causes, slip_allowed
from app.orchestrator.types import CatalogItem, SessionState


@dataclass(frozen=True)
class Assessment:
    posterior: Posterior
    view: ReasonView


def assess(
    item: CatalogItem,
    response: str,
    learner: LearnerState,
    session: SessionState,
    *,
    prior: Posterior | None = None,
    confidence: Confidence | None = None,
    config: ReasonConfig = DEFAULT_CONFIG,
) -> Assessment:
    """Weigh every cause that could explain this wrong answer, given what was seen before."""
    found = find_causes(item, response, session, slip_allowed=slip_allowed(item, learner, session))
    matched = tuple(cause_id(d.kind, d.detail) for d in found)
    posterior = update(
        prior, likelihoods(matched, confidence=confidence, config=config), config=config
    )
    return Assessment(posterior, view(posterior, config=config))
