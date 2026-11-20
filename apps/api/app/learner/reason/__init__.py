"""Reason model: why a learner gave an answer, as shares of belief (not one hard label)."""

from app.learner.reason.assess import Assessment, assess
from app.learner.reason.config import DEFAULT_CONFIG, OTHER, ReasonConfig
from app.learner.reason.posterior import (
    Band,
    Confidence,
    Posterior,
    ReasonView,
    apply_correction,
    cause_id,
    cause_kind,
    likelihoods,
    update,
    view,
)

__all__ = [
    "DEFAULT_CONFIG",
    "OTHER",
    "Assessment",
    "Band",
    "Confidence",
    "Posterior",
    "ReasonConfig",
    "ReasonView",
    "apply_correction",
    "assess",
    "cause_id",
    "cause_kind",
    "likelihoods",
    "update",
    "view",
]
