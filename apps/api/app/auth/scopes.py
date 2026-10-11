from __future__ import annotations

from collections.abc import Iterable

CONSENT_SCOPES = frozenset(
    {
        "tutoring",
        "teacher_share",
        "research_pseudonymised",
        "ai_processing",
        "free_text",
        "uploads",
    }
)
# Everything except plain tutoring needs a guardian's informed choice; a guest never grants these.
GUARDIAN_ONLY_SCOPES = CONSENT_SCOPES - {"tutoring"}


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
