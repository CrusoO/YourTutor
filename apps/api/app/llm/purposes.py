"""LLM purposes (ARCHITECTURE section 14). One function each; prompts are versioned files."""

from __future__ import annotations

from enum import StrEnum


class Purpose(StrEnum):
    personalise_hint = "personalise_hint"
    adapt_explanation = "adapt_explanation"
    answer_doubt = "answer_doubt"  # stubbed until G7 (Study Mode Ask)
    grade_explain_back = "grade_explain_back"
    encourage = "encourage"
    draft_content = "draft_content"  # authoring tool only, never at runtime


RUNTIME_PURPOSES: frozenset[Purpose] = frozenset(
    {
        Purpose.personalise_hint,
        Purpose.adapt_explanation,
        Purpose.grade_explain_back,
        Purpose.encourage,
    }
)

PROMPT_VERSION = "v1"

# Fields a purpose needs besides the shared ones (source, glossary, forbidden answer, band).
REQUIRED_FIELDS: dict[Purpose, tuple[str, ...]] = {
    Purpose.personalise_hint: ("item_stem", "hint_level", "authored_hint"),
    Purpose.adapt_explanation: ("item_stem",),
    Purpose.grade_explain_back: ("student_text", "rubric"),
    Purpose.encourage: ("trigger",),
}
# Optional fields are filled with an empty string so the template always formats.
OPTIONAL_FIELDS: dict[Purpose, tuple[str, ...]] = {
    Purpose.personalise_hint: ("misconception",),
}
