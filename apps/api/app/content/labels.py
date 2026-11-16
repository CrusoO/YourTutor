"""The exact label strings for practice questions (owner's rights research, 2026-11-11).

These are fixed wording. Change them only on the owner's say-so. The API serves the item labels
on a practice item that is original and Tier A; the footer disclaimer is also in the web copy file.
"""

from __future__ import annotations

from collections.abc import Sequence

QUESTION_LABEL = (
    "Original Brownie practice question. Aligned to the CBSE Class 10 syllabus (2026-27). "
    "Not an official CBSE or NCERT question."
)
PATTERN_TAG_TEMPLATE = (
    "Question type seen in CBSE Class 10 board papers: {marks}-mark {type} ({years})."
)
VERIFICATION_BADGE = "Answer checked by calculation"
REVIEWED_BADGE = "Reviewed by a teacher"
# What a stamped item may say about itself: one sentence per honest label. The factory has no
# wording for "human-reviewed" or "teacher-approved" because it can never earn them.
FACTORY_LABEL_TEXT = {
    "calculation-checked": "Answer checked by calculation: two independent methods agree.",
    "fact-checked-against-sources": "Facts checked against two independent sources.",
    "diagram-spec-checked": "Diagram labels checked against the figure specification.",
}
FOOTER_DISCLAIMER = (
    "Brownie is independent and is not affiliated with, endorsed by or approved by CBSE, NCERT, "
    "or Nepal's CDC or NEB. These names are used only to describe syllabus alignment. "
    "Official papers: cbseacademic.nic.in."
)


def pattern_tag(marks: int, question_type: str, years: Sequence[int]) -> str:
    """Fill the pattern tag. `question_type` is spoken with spaces (assertion_reason becomes
    "assertion reason")."""
    spoken = question_type.replace("_", " ")
    year_text = ", ".join(str(year) for year in sorted(set(years)))
    return PATTERN_TAG_TEMPLATE.format(marks=marks, type=spoken, years=year_text)


def item_labels(
    *,
    pool: str,
    tier: str | None,
    original: bool,
    reviewed: bool,
    pattern: str | None,
    verification_label: str | None = None,
) -> dict[str, str] | None:
    """Labels for one item, or None. Only practice items that are original and Tier A get them."""
    if pool != "practice" or tier != "A" or not original:
        return None
    labels = {"question": QUESTION_LABEL, "badge": VERIFICATION_BADGE}
    if reviewed:
        labels["reviewed"] = REVIEWED_BADGE
    if pattern:
        labels["pattern"] = pattern
    if verification_label in FACTORY_LABEL_TEXT:
        labels["verification"] = FACTORY_LABEL_TEXT[verification_label]
    return labels
