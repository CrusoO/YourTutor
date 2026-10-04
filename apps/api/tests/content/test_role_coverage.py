from __future__ import annotations

from app.content.schema import ContentStatus
from app.content.stem_solve import check_item_stem_answer
from app.content.validator import load_bundle, validate_path
from app.registries.paths import repo_root

CONTENT = repo_root() / "content"
NEW_ROLES = {"explain", "apply", "transfer"}
# Reason-choice explain items cannot be machine-verified; a teacher signs them off.
TEACHER_CHECKED = {"ITEM.LIN1.R.0001", "ITEM.LIN1.R.0004", "ITEM.LIN1.R.0007", "ITEM.LIN1.R.0031"}


def _role_items():
    return [i for i in load_bundle(CONTENT).items if i.id.startswith("ITEM.LIN1.R.")]


def test_every_seed_skill_has_explain_apply_and_transfer_practice_items() -> None:
    bundle = load_bundle(CONTENT)
    for skill in bundle.skills:
        roles = {
            item.role.value
            for item in bundle.items
            if item.primary_skill == skill.id and item.pool.value == "practice"
        }
        assert NEW_ROLES <= roles, (skill.id, roles)


def test_new_role_items_are_exactly_three_per_skill_in_draft() -> None:
    items = _role_items()
    assert len(items) == 36
    by_skill: dict[str, list[str]] = {}
    for item in items:
        by_skill.setdefault(item.primary_skill, []).append(item.role.value)
        assert item.status == ContentStatus.draft
        assert item.pool.value == "practice"
        assert item.reviewed_by is None
        assert item.stem.ne is not None and item.stem.ne.startswith("<Nepali")
        assert item.stem.as_ is not None and item.stem.as_.startswith("<Assamese")
    assert len(by_skill) == 12
    for skill, roles in by_skill.items():
        assert sorted(roles) == ["apply", "explain", "transfer"], skill


def test_seed_with_role_items_validates_without_errors() -> None:
    report = validate_path(CONTENT)
    assert report.errors == []


def test_new_items_have_machine_verified_answers_except_reason_choice_items() -> None:
    for item in _role_items():
        result = check_item_stem_answer(item)
        if item.id in TEACHER_CHECKED:
            assert result == "teacher", item.id
        else:
            assert result is None, (item.id, result)


def test_teacher_check_list_matches_the_reason_choice_items() -> None:
    report = validate_path(CONTENT)
    flagged = {i for i in report.needs_teacher_check if i.startswith("ITEM.LIN1.R.")}
    assert flagged == TEACHER_CHECKED


def test_difficulty_tiers_follow_role() -> None:
    tiers = {"explain": 0.45, "apply": 0.6, "transfer": 0.85}
    for item in _role_items():
        assert item.difficulty == tiers[item.role.value], item.id
