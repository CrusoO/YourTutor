"""Hook for a second-chance machine check of numeric drafts. Deliberately unused.

No general recomputation from a stem is attempted: a stem that merely mentions numbers is not an
explicit arithmetic relation, and a wrong "check" would be worse than none. A lane that can really
recompute a family of stems may register a checker here later. Even then the lint only reports the
result as information. It never marks an item machine-checked: only the factory stamp step may
produce a verification record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Recheck:
    """What a registered checker found for one numeric draft."""

    agrees: bool
    method: str
    detail: str = ""


class NumericRecheck(Protocol):
    def __call__(self, *, stem: str, correct: str, unit: str) -> Recheck | None:
        """Return None when this checker does not apply to the stem."""


# Empty on purpose. Lint reads this list; nothing registers into it today.
NUMERIC_RECHECKS: list[NumericRecheck] = []
