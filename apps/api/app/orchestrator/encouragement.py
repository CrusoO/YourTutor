"""Encouragement triggers and variants (TUTOR_CONSTITUTION rules 9, 11, 16). Pure.

Encouragement appears only on a trigger: a hard-tier success, a recovery after a failure on the
same skill, or the end of a session (never after a failure, never after an easy item, never on
consecutive items). The policy picks a variant id; the authored text lives in
`content/copy/encouragement.yaml` and is resolved per language when the action is sent.
"""

from __future__ import annotations

TRIGGERS = ("hard_success", "recovery", "session_end")

# Variant ids per trigger. Every id needs an authored text in content/copy/encouragement.yaml.
VARIANTS: dict[str, tuple[str, ...]] = {
    "hard_success": ("checked_the_answer", "worked_step_by_step"),
    "recovery": ("kept_trying", "tried_a_new_way"),
    "session_end": ("steady_work", "come_back_anytime"),
}


def pick_variant(trigger: str, count: int) -> str:
    """Deterministic: cycle through the variants of a trigger as encouragement is shown."""
    options = VARIANTS[trigger]
    return options[count % len(options)]
