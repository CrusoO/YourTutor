from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    """One consent scope and the switches around it.

    `flag_setting` names the Settings attribute that switches the scope on (None: no switch).
    `text_scope` names the folder under config/consent_texts that holds its wording (None: no
    versioned text yet). `deletion_handler_id` names what withdrawing the scope must delete; the
    handlers themselves arrive in a later PR.
    """

    id: str
    guardian_only: bool = True
    guest_allowed: bool = False
    flag_setting: str | None = None
    text_scope: str | None = None
    deletion_handler_id: str | None = None


SCOPE_REGISTRY: dict[str, Scope] = {
    s.id: s
    for s in (
        Scope("tutoring", guardian_only=False, guest_allowed=True),
        Scope(
            "teacher_share",
            flag_setting="scope_teacher_share_enabled",
            deletion_handler_id="teacher_share_rows",
        ),
        Scope(
            "research_pseudonymised",
            flag_setting="scope_research_enabled",
            deletion_handler_id="research_rows",
        ),
        Scope(
            "ai_processing",
            flag_setting="scope_ai_processing_enabled",
            deletion_handler_id="llm_call_rows",
        ),
        Scope("free_text"),  # deprecated: read as ai_help_typed
        Scope("uploads"),  # deprecated: read as photo_check
        Scope(
            "learning_profile",
            flag_setting="learner_profile_enabled",
            text_scope="learning_profile",
            deletion_handler_id="learner_profile_rows",
        ),
        Scope(
            "math_check",
            flag_setting="scope_math_check_enabled",
            text_scope="math_check",
            deletion_handler_id="none_stored",
        ),
        Scope(
            "photo_check",
            flag_setting="scope_photo_check_enabled",
            text_scope="photo_check",
            deletion_handler_id="none_stored",
        ),
        Scope(
            "ai_help_typed",
            flag_setting="scope_ai_help_typed_enabled",
            text_scope="ai_help_typed",
            deletion_handler_id="llm_call_rows",
        ),
    )
}

CONSENT_SCOPES = frozenset(SCOPE_REGISTRY)
# Everything except plain tutoring needs a guardian's informed choice; a guest never grants these.
GUARDIAN_ONLY_SCOPES = frozenset(s.id for s in SCOPE_REGISTRY.values() if s.guardian_only)
# Scopes introduced by the consent closure: granting one needs its flag on and its text approved.
NEW_SCOPES = frozenset({"math_check", "photo_check", "ai_help_typed"})
# Old scope -> the scope that replaces it. Applied when reading a stored grant, never when writing.
DEPRECATED_ALIASES: dict[str, str] = {"free_text": "ai_help_typed", "uploads": "photo_check"}


def read_scopes(stored: Iterable[str]) -> set[str]:
    """Scopes of a stored grant as the app should read them: old names also count as their
    replacements. The stored row is never rewritten."""
    out = set(stored)
    out |= {DEPRECATED_ALIASES[s] for s in out if s in DEPRECATED_ALIASES}
    return out


def scope_error(scopes: Iterable[str], *, guest: bool, available: Iterable[str]) -> str | None:
    """Why this scope list may not be granted, or None. Pure: the server runs it on every grant."""
    wanted = set(scopes)
    unknown = wanted - CONSENT_SCOPES
    if unknown:
        return f"unknown scopes: {sorted(unknown)}"
    if guest and wanted & GUARDIAN_ONLY_SCOPES:
        return f"guests cannot grant: {sorted(wanted & GUARDIAN_ONLY_SCOPES)}"
    unavailable = wanted - set(available)
    if unavailable:
        return f"scopes not available here: {sorted(unavailable)}"
    return None
