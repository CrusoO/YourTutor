"""Turn a typed message into an action directive, or into nothing.

The reply only ever carries values this module chose (a registered name, a client verb, validated
arguments and authored narration). The student's own words are never echoed back or executed, and
only the student's message is considered: lesson text, page content and model output never reach
this function.
"""

from __future__ import annotations

from typing import Any

from app.actions.matcher import ActionConfig, action_config, match_utterance, phrases_for
from app.actions.registry import REGISTRY, Risk, Tier
from app.ask.config import load_safety
from app.ask.guard import clean_question, screen

NONE: dict[str, Any] = {"kind": "none"}


def route(
    utterance: str, language: str, tier: Tier, config: ActionConfig | None = None
) -> dict[str, Any]:
    """`{kind:"none"}` (carry on to the tutor), `{kind:"denied"}` or `{kind:"action"}`."""
    config = config or action_config()
    cleaned = clean_question(utterance, config.max_chars)
    if cleaned.empty or cleaned.too_long:
        return dict(NONE)
    # A distressed, unsafe or injected message is never a command; the tutor flow handles it.
    if screen(cleaned.text, load_safety(language)).kind != "ok":
        return dict(NONE)

    hit = match_utterance(cleaned.text, config, language)
    if hit is None:
        return dict(NONE)
    spec = REGISTRY[hit.action]
    phrases = phrases_for(config, language)

    if tier not in spec.tiers:
        fallback = config.messages.get(config.default_language, {}).get("denied", "")
        return {
            "kind": "denied",
            "name": spec.name,
            "narration": phrases.denied.get(spec.name, fallback),
        }

    args = spec.args_for(hit.value)
    if args is None:  # the config named a value the registry does not allow: do nothing
        return dict(NONE)
    out: dict[str, Any] = {
        "kind": "action",
        "name": spec.name,
        "client": spec.client,
        "args": args,
        "risk": spec.risk.value,
        "narration": phrases.narration[spec.name],
    }
    if spec.risk is Risk.CONFIRM:
        out["confirm"] = phrases.confirm.get(spec.name, "")
    return out
