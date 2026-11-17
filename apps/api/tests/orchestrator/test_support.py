from __future__ import annotations

import ast
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

import app.orchestrator.support as support_mod
from app.orchestrator.support import (
    DEFAULT_CONFIG,
    AttemptOutcome,
    SupportConfig,
    hidden_steps,
    initial_support,
    next_support,
    support_after,
    support_from_recent,
)
from app.orchestrator.support_config import load_support_config, support_config_from_mapping

CLEAN = AttemptOutcome(True)
HINTED = AttemptOutcome(True, hinted=True)
MISS = AttemptOutcome(False)
REVEAL = AttemptOutcome(False, revealed=True)

outcomes = st.sampled_from([CLEAN, HINTED, MISS, REVEAL])
supports = st.sampled_from(["full", "partial", "problems"])


@pytest.mark.parametrize(
    ("p", "label", "age", "expected"),
    [
        (0.10, "unclear", None, "full"),
        (0.60, "not_known", None, "full"),
        (0.25, "unclear", None, "partial"),  # boundary: 0.25 is not below 0.25
        (0.2499, "known", None, "full"),
        (0.70, "known", None, "partial"),  # boundary: 0.70 is not above 0.70
        (0.7001, "known", None, "problems"),
        (0.95, "unclear", None, "partial"),
        (0.95, "known", 21.0, "problems"),  # exactly 21 days is not stale
        (0.95, "known", 21.1, "partial"),
        (0.95, "known", 400.0, "partial"),
        (0.10, "known", 400.0, "full"),
        (0.0, "not_known", None, "full"),
        (1.0, "known", 0.0, "problems"),
    ],
)
def test_initial_support(p: float, label: str, age: float | None, expected: str) -> None:
    assert initial_support(p, label, age) == expected


@pytest.mark.parametrize(
    ("args"),
    [(0.5, "maybe", None), (-0.1, "known", None), (1.1, "known", None), (0.5, "known", -1)],
)
def test_initial_support_rejects_bad_input(args: tuple) -> None:
    with pytest.raises(ValueError):
        initial_support(*args)


def test_fading_and_raising_one_step() -> None:
    assert next_support("full", [CLEAN, CLEAN]) == "partial"
    assert next_support("partial", [CLEAN, CLEAN]) == "problems"
    assert next_support("problems", [CLEAN, CLEAN]) == "problems"  # floor
    assert next_support("problems", [MISS, MISS]) == "partial"
    assert next_support("partial", [MISS, MISS]) == "full"
    assert next_support("full", [MISS, MISS]) == "full"  # ceiling
    assert next_support("problems", [CLEAN, REVEAL]) == "partial"  # one reveal is enough
    assert next_support("partial", []) == "partial"


def test_hinted_correct_does_not_fade_or_raise() -> None:
    assert next_support("partial", [CLEAN, HINTED]) == "partial"
    assert next_support("partial", [HINTED, HINTED]) == "partial"
    assert next_support("partial", [CLEAN, MISS]) == "partial"  # one miss is not two


def test_one_clean_is_not_enough_two_are() -> None:
    assert next_support("full", [CLEAN]) == "full"
    assert next_support("full", [MISS, CLEAN, CLEAN]) == "partial"


def test_hysteresis_one_change_per_two_items() -> None:
    # CLEAN x2 -> partial at item 2; the next item cannot move again.
    assert support_after("full", [CLEAN, CLEAN]) == "partial"
    # starting problems: miss, miss -> partial after item 2 (one change)
    assert support_after("problems", [MISS, MISS]) == "partial"
    # reveal at item 1 moves up at once; the second item is inside the hysteresis window
    assert support_after("problems", [REVEAL, REVEAL]) == "partial"
    assert support_after("problems", [REVEAL]) == "partial"
    assert support_after("full", []) == "full"


def test_support_after_three_items_forgets_the_start() -> None:
    history = [CLEAN, CLEAN, CLEAN]
    assert {support_after(s, history) for s in ("full", "partial", "problems")} == {"problems"}
    history = [CLEAN, MISS, MISS]
    assert {support_after(s, history) for s in ("full", "partial", "problems")} == {"full"}


def test_support_from_recent_cases() -> None:
    assert support_from_recent([CLEAN, CLEAN, CLEAN]) == "problems"
    assert support_from_recent([MISS, CLEAN, CLEAN]) == "partial"
    assert support_from_recent([CLEAN, CLEAN, HINTED]) == "partial"
    assert support_from_recent([CLEAN, CLEAN, REVEAL]) == "full"
    assert support_from_recent([CLEAN, MISS, MISS]) == "full"
    assert support_from_recent([MISS] * 6 + [CLEAN, CLEAN, CLEAN]) == "problems"
    with pytest.raises(ValueError):
        support_from_recent([])


@given(history=st.lists(outcomes, min_size=3, max_size=12), a=supports, b=supports)
def test_property_k_initial_label_never_decides_after_three(history, a, b) -> None:
    assert support_after(a, history) == support_after(b, history)


@given(
    history=st.lists(outcomes, min_size=3, max_size=12),
    prefix=st.lists(outcomes, max_size=6),
    p=st.floats(0, 1),
    label=st.sampled_from(["known", "unclear", "not_known"]),
    age=st.one_of(st.none(), st.floats(0, 500)),
)
def test_property_k_via_probe_label_and_older_history(history, prefix, p, label, age) -> None:
    start = initial_support(p, label, age)
    last3 = history[-3:]
    assert support_after(start, prefix + last3) == support_from_recent(last3)


@given(start=supports, history=st.lists(outcomes, max_size=2))
def test_support_after_moves_at_most_one_level_early(start, history) -> None:
    order = ["full", "partial", "problems"]
    assert abs(order.index(support_after(start, history)) - order.index(start)) <= 1


def test_hidden_steps_full_fades_zero_one_two_all() -> None:
    assert [hidden_steps("full", 5, i) for i in range(5)] == [0, 1, 2, 5, 5]
    assert hidden_steps("full", 1, 2) == 1  # never more than the total
    assert hidden_steps("full", 0, 0) == 0
    assert hidden_steps("full", 0, 9) == 0


def test_hidden_steps_partial_and_problems() -> None:
    assert hidden_steps("partial", 4, 0) == 3
    assert hidden_steps("partial", 1, 0) == 0
    assert hidden_steps("partial", 0, 0) == 0
    assert hidden_steps("problems", 4, 0) == 4
    assert hidden_steps("problems", 0, 3) == 0


@given(s=supports, total=st.integers(0, 30), idx=st.integers(0, 30))
def test_hidden_steps_bounded(s, total, idx) -> None:
    assert 0 <= hidden_steps(s, total, idx) <= total


def test_hidden_steps_rejects_negatives() -> None:
    with pytest.raises(ValueError):
        hidden_steps("full", -1, 0)
    with pytest.raises(ValueError):
        hidden_steps("full", 3, -1)


def test_outcome_validation_and_flags() -> None:
    with pytest.raises(ValueError):
        AttemptOutcome(True, revealed=True)
    assert CLEAN.clean and not CLEAN.miss
    assert not HINTED.clean and not HINTED.miss
    assert MISS.miss and REVEAL.miss


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        SupportConfig(full_below=0.8, problems_above=0.5)
    with pytest.raises(ValueError):
        SupportConfig(decide_after_items=1)  # smaller than the fade window
    with pytest.raises(ValueError):
        SupportConfig(fade_after_clean=0)
    with pytest.raises(ValueError):
        SupportConfig(stale_after_days=0)


def test_yaml_matches_defaults_and_every_number_is_tunable_default() -> None:
    assert load_support_config() == DEFAULT_CONFIG
    from app.registries.paths import config_dir

    lines = (config_dir() / "support.yaml").read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines):
        if line and not line.startswith("#") and ":" in line:
            assert "TUNABLE-DEFAULT" in lines[number - 1] or lines[number - 1].startswith("#")
    assert sum("TUNABLE-DEFAULT" in line for line in lines) >= 8


def test_loader_rejects_unknown_and_missing_keys() -> None:
    with pytest.raises(ValueError, match="unknown"):
        support_config_from_mapping({"nope": 1})
    with pytest.raises(ValueError):
        support_config_from_mapping({"fade_after_clean": "x"} | {"decide_after_items": 3})


def test_support_module_is_pure() -> None:
    tree = ast.parse(Path(support_mod.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    banned = ("app", "random", "time", "datetime", "logging", "yaml", "os")
    assert not [n for n in names if n.split(".")[0] in banned], names
