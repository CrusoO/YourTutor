"""A share of belief for each possible cause of a wrong answer. Pure, no I/O.

An answer rarely proves one cause. `12` for `15 - 3` could be a held belief, a slip or a guess, so
the model keeps a weight for each, updates it with every answer, and only names a cause when one
clearly leads. Below that it says "unclear", and the player asks one more question instead.

A cause id is `kind` or `kind:detail` (`misconception:MC.SIGN`, `slip:sign_flip`, `other`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.learner.reason.config import DEFAULT_CONFIG, KINDS, OTHER, ReasonConfig

Band = Literal["likely", "maybe", "unclear"]
Confidence = Literal["sure", "unsure"]


def cause_id(kind: str, detail: str | None = None) -> str:
    return f"{kind}:{detail}" if detail else kind


def cause_kind(cause: str) -> str:
    return cause.split(":", 1)[0]


@dataclass(frozen=True)
class Posterior:
    """Weights that add up to 1, strongest first. Immutable, so a stale copy is never edited."""

    weights: tuple[tuple[str, float], ...]

    @staticmethod
    def from_mapping(raw: Mapping[str, float]) -> Posterior:
        total = sum(v for v in raw.values() if v > 0)
        if total <= 0:
            return Posterior(((OTHER, 1.0),))
        pairs = [(k, v / total) for k, v in raw.items() if v > 0]
        pairs.sort(key=lambda kv: (-kv[1], kv[0]))
        return Posterior(tuple(pairs))

    def get(self, cause: str) -> float:
        return dict(self.weights).get(cause, 0.0)

    def as_dict(self) -> dict[str, float]:
        return dict(self.weights)

    def top(self) -> tuple[str, float]:
        return self.weights[0]

    def runner_up(self) -> float:
        return self.weights[1][1] if len(self.weights) > 1 else 0.0


@dataclass(frozen=True)
class ReasonView:
    """What the rest of the player may use: the leading cause, how sure we are, and the rivals."""

    cause: str | None  # None when the lead is only "other" or the evidence is unclear
    share: float
    band: Band
    rivals: tuple[str, ...]  # other named causes still in play, strongest first

    @property
    def needs_followup(self) -> bool:
        return self.band != "likely"

    def as_payload(self) -> dict[str, object]:
        return {
            "cause": self.cause,
            "share": round(self.share, 2),
            "band": self.band,
            "rivals": list(self.rivals),
        }


def _likelihood_for(kind: str, config: ReasonConfig) -> float:
    return {
        "misconception": config.lik_misconception,
        "prerequisite_gap": config.lik_prerequisite_gap,
        "slip": config.lik_slip,
        "incomplete_procedure": config.lik_incomplete_procedure,
    }.get(kind, config.lik_other)


def likelihoods(
    matched: tuple[str, ...],
    *,
    confidence: Confidence | None = None,
    config: ReasonConfig = DEFAULT_CONFIG,
) -> dict[str, float]:
    """How well each cause explains the answer just given.

    `matched` holds the ids of every authored cause whose signature equals the answer. `other` is
    always added, so an answer nobody wrote down is explained by "something else", not forced onto
    the nearest label. The learner's confidence then scales each kind.
    """
    raw = {cid: _likelihood_for(cause_kind(cid), config) for cid in matched}
    raw[OTHER] = config.lik_other
    if confidence is None:
        return raw
    boost = config.sure_boost if confidence == "sure" else config.unsure_boost
    return {cid: v * boost.get(cause_kind(cid), 1.0) for cid, v in raw.items()}


def update(
    prior: Posterior | None,
    lik: Mapping[str, float],
    *,
    config: ReasonConfig = DEFAULT_CONFIG,
) -> Posterior:
    """Bayes with forgetting: older evidence fades a little, then the new answer is weighed in."""
    if prior is None:
        return Posterior.from_mapping(dict(lik))
    even = 1.0 / max(len(prior.weights), 1)
    faded = {c: (1 - config.forget) * w + config.forget * even for c, w in prior.weights}
    causes = set(faded) | set(lik)
    out: dict[str, float] = {}
    for cause in causes:
        before = faded.get(cause, config.unseen_prior)
        out[cause] = before * lik.get(cause, config.lik_absent)
    return Posterior.from_mapping(out)


def apply_correction(
    post: Posterior, cause: str, *, config: ReasonConfig = DEFAULT_CONFIG
) -> Posterior:
    """The learner said "that's not why": the named cause keeps only a small share."""
    scaled = {c: (w * config.correction_factor if c == cause else w) for c, w in post.weights}
    if cause not in scaled:
        return post
    if set(scaled) == {cause}:  # nothing else to fall back on
        scaled[OTHER] = scaled.get(OTHER, 0.0) + 1.0
    return Posterior.from_mapping(scaled)


def view(post: Posterior | None, *, config: ReasonConfig = DEFAULT_CONFIG) -> ReasonView:
    """Reduce the weights to what the player needs. `other` alone never becomes a named cause."""
    if post is None:
        return ReasonView(None, 0.0, "unclear", ())
    named = [(c, w) for c, w in post.weights if cause_kind(c) in KINDS and c != OTHER]
    if not named:
        return ReasonView(None, post.get(OTHER), "unclear", ())
    top, share = named[0]
    lead = share - (named[1][1] if len(named) > 1 else 0.0)
    other = post.get(OTHER)
    if share >= config.band_likely and lead >= config.band_margin and share > other:
        band: Band = "likely"
    elif share >= config.band_maybe and share > other:
        band = "maybe"
    else:
        band = "unclear"
    rivals = tuple(c for c, _ in named[1:3])
    return ReasonView(top if band != "unclear" else None, share, band, rivals)
