"""The closed list of things Brownie can do on a student's behalf.

An action is never open-ended: it has a fixed name, a fixed client verb the web app already
knows, a risk level and the tiers that may use it. Anything else a student types is not an
action and goes on to the tutor. Adding an action means adding a row here, a phrase block in
`config/actions.yaml` and a test; nothing is discovered from content, a lesson or a page.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


class Tier(StrEnum):
    """Who is asking. Unknown or unverified age is treated as the narrowest tier."""

    GUEST = "guest"
    STUDENT = "student"


class Risk(StrEnum):
    SAFE = "safe"  # runs at once
    CONFIRM = "confirm"  # the student must say yes first


@dataclass(frozen=True)
class ActionSpec:
    name: str
    client: str  # the verb the web app executes; it ignores any verb it does not know
    risk: Risk
    tiers: frozenset[Tier]
    fixed_args: Mapping[str, str] = field(default_factory=dict)
    # One optional argument whose value must be one of `arg_values`.
    arg_name: str | None = None
    arg_values: frozenset[str] = frozenset()

    def args_for(self, value: str | None) -> dict[str, str] | None:
        """The validated arguments, or None when the value is not allowed for this action."""
        args = dict(self.fixed_args)
        if self.arg_name is None:
            return args if value is None else None
        if value is None or value not in self.arg_values:
            return None
        args[self.arg_name] = value
        return args


_BOTH = frozenset({Tier.GUEST, Tier.STUDENT})

_SPECS = (
    ActionSpec("start_practice", "start_practice", Risk.SAFE, _BOTH),
    ActionSpec("continue_learning", "open_screen", Risk.SAFE, _BOTH, {"screen": "today"}),
    ActionSpec("show_subjects", "open_screen", Risk.SAFE, _BOTH, {"screen": "subjects"}),
    ActionSpec(
        "switch_language",
        "set_language",
        Risk.SAFE,
        _BOTH,
        arg_name="language",
        arg_values=frozenset({"en", "hi"}),
    ),
    ActionSpec("new_chat", "new_chat", Risk.CONFIRM, _BOTH),
    # Narration only until sign-in is built (A4): the web shows the words and does nothing else.
    ActionSpec("sign_in_prompt", "none", Risk.SAFE, frozenset({Tier.GUEST})),
    ActionSpec("help", "none", Risk.SAFE, _BOTH),
)

REGISTRY: Mapping[str, ActionSpec] = MappingProxyType({spec.name: spec for spec in _SPECS})
