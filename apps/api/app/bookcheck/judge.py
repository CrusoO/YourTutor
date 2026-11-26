"""Hook for a model-based judge ("option B"). It is OFF, NOT WIRED, and has no implementation.

A judge would take one of our items plus a few book snippets and return a verdict. That means
sending book text to a model, which this project does not do. Nothing in this package imports or
calls this module. Implementing or enabling it needs the owner's explicit approval, a decision on
the licence and privacy side, and a separate change. Until then book text stays on this machine
and is only ever compared by the deterministic code in this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Evidence:
    snippets: list[str]


class Judge(Protocol):
    """item + evidence -> verdict (agree | not_found | possible_conflict | needs_human)."""

    def judge(self, item_id: str, item_text: str, evidence: Evidence) -> str: ...
