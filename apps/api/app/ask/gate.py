"""Layer C: the relevance gate (ARCHITECTURE section 12.1). Pure.

Strong match -> answer. Close matches across different skills -> clarify with choices. Weak or
no match -> out of scope, which is logged as a content gap. There is no web fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ask.config import AskConfig, ask_config
from app.ask.search import Hit


@dataclass(frozen=True)
class GateDecision:
    kind: str  # answer | clarify | out_of_scope
    hits: tuple[Hit, ...] = ()  # the passages to answer from
    choices: tuple[Hit, ...] = field(default=())  # one per skill, for clarify
    reason: str = ""


def decide(hits: list[Hit], cfg: AskConfig | None = None) -> GateDecision:
    cfg = cfg or ask_config()
    if not hits:
        return GateDecision("out_of_scope", reason="no_passages")
    top = hits[0]
    if top.score < cfg.clarify_min:
        return GateDecision("out_of_scope", reason="weak_match")
    rivals = [
        h
        for h in hits[1:]
        if set(h.skill_ids).isdisjoint(top.skill_ids)
        and top.score - h.score <= cfg.ambiguity_margin
        and h.score >= cfg.clarify_min
    ]
    if rivals or top.score < cfg.answer_min:
        picked: list[Hit] = []
        seen: set[tuple[str, ...]] = set()
        for hit in hits:
            if hit.score >= cfg.clarify_min and hit.skill_ids not in seen:
                seen.add(hit.skill_ids)
                picked.append(hit)
        if len(picked) >= 2 or top.score < cfg.answer_min:
            return GateDecision("clarify", choices=tuple(picked[: cfg.choices]), reason="ambiguous")
    same = tuple(h for h in hits if not set(h.skill_ids).isdisjoint(top.skill_ids))
    return GateDecision("answer", hits=same or (top,), reason="strong_match")
