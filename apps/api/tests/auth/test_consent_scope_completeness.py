"""Fails when a consent scope has no deletion handler or no consent text file.

Every scope a guardian can be asked about must say what withdrawing it deletes and, once it has
approved wording, have that wording on disk for both audiences. A scope added later without them
breaks this test.
"""

from __future__ import annotations

import pytest

from app.auth import consent_texts as ct
from app.auth.scopes import DEPRECATED_ALIASES, SCOPE_REGISTRY

# Scopes that exist from before the consent closure. Their wording still lives in the web app and
# moves to text files in a later step; shrink this set as each one gets files, never grow it.
LEGACY_WITHOUT_TEXT = frozenset(
    {"tutoring", "teacher_share", "research_pseudonymised", "ai_processing"}
)
LIVE = sorted(s for s in SCOPE_REGISTRY if s not in DEPRECATED_ALIASES)


@pytest.mark.parametrize("scope", [s for s in LIVE if s != "tutoring"])
def test_every_live_scope_names_what_its_withdrawal_deletes(scope: str) -> None:
    assert SCOPE_REGISTRY[scope].deletion_handler_id, f"{scope} has no deletion handler"


def test_tutoring_is_closed_by_deleting_the_account_not_by_a_scope_handler() -> None:
    # withdrawing tutoring ends all consent and the family purge removes everything (see retention)
    assert SCOPE_REGISTRY["tutoring"].deletion_handler_id is None


@pytest.mark.parametrize("scope", LIVE)
def test_every_live_scope_has_text_files_unless_it_is_a_listed_legacy_scope(scope: str) -> None:
    entry = SCOPE_REGISTRY[scope]
    if scope in LEGACY_WITHOUT_TEXT:
        assert entry.text_scope is None, f"{scope} now has text: remove it from LEGACY_WITHOUT_TEXT"
        return
    assert entry.text_scope, f"{scope} has no consent text"
    for audience in ct.AUDIENCES:
        found = list((ct.texts_root() / entry.text_scope).glob(f"v*.en.{audience}.md"))
        assert found, f"{scope} lacks a {audience} text file"
    assert ct.current_manifest(entry.text_scope), f"{scope} text does not match the manifest"


def test_deprecated_scopes_point_at_a_scope_that_is_complete() -> None:
    for old, new in DEPRECATED_ALIASES.items():
        assert new in SCOPE_REGISTRY and SCOPE_REGISTRY[new].text_scope
        assert SCOPE_REGISTRY[new].deletion_handler_id, old
