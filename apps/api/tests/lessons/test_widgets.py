"""Widget goal predicates: shared fixtures (the TS mirror runs the same files) plus properties."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import TypeAdapter

from app.lessons.schema import BalanceScaleWidget, FunctionGraphWidget, WidgetSpec
from app.lessons.widgets import goal_met, verify_widget_result
from app.registries.paths import repo_root

DIR = repo_root() / "packages" / "shared" / "fixtures" / "widgets"
FILES = sorted(DIR.glob("*.json"))
ADAPTER: TypeAdapter[Any] = TypeAdapter(WidgetSpec)  # type: ignore[arg-type]


def _widget(path: Path) -> tuple[BalanceScaleWidget | FunctionGraphWidget, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return ADAPTER.validate_python(data["widget"]), data["cases"]


def test_both_initial_widget_types_have_fixtures() -> None:
    assert [p.stem for p in FILES] == ["balance_scale", "function_graph"]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_widget_fixture_cases(path: Path) -> None:
    widget, cases = _widget(path)
    assert len(cases) >= 10
    for case in cases:
        assert goal_met(widget, case["state"]) is case["goal_met"], case["name"]


def test_verify_widget_result_accepts_a_solved_state_and_rejects_a_forged_one() -> None:
    widget, _ = _widget(DIR / "balance_scale.json")
    ok = {
        "widget_id": "W.BALANCE",
        "final_state": {"lb": 1, "lw": 0, "rb": 0, "rw": 4},
        "actions_count": 9,
    }
    assert verify_widget_result(widget, ok) == (True, None)
    forged = {**ok, "final_state": {"lb": 2, "lw": 3, "rb": 0, "rw": 11}}
    assert verify_widget_result(widget, forged) == (False, "widget_goal_not_met")


def test_verify_widget_result_rejects_malformed_payloads() -> None:
    widget, _ = _widget(DIR / "function_graph.json")
    assert verify_widget_result(widget, {"widget_id": "W.GRAPH"})[1] == "widget_result_malformed"
    assert verify_widget_result(widget, {"widget_id": "OTHER", "final_state": {"x": 4}})[1] == (
        "widget_id_mismatch"
    )
    assert verify_widget_result(widget, "x=4")[1] == "widget_result_malformed"  # type: ignore[arg-type]


@given(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False))
def test_graph_goal_only_at_the_solution(x: float) -> None:
    widget, _ = _widget(DIR / "function_graph.json")
    if abs(x - 4) > 1e-5:
        assert goal_met(widget, {"x": x}) is False


@given(st.integers(-3, 20), st.integers(-3, 20), st.integers(-3, 20), st.integers(-3, 20))
def test_balance_goal_requires_exactly_one_box_and_the_box_weight(
    lb: int, lw: int, rb: int, rw: int
) -> None:
    widget, _ = _widget(DIR / "balance_scale.json")
    if goal_met(widget, {"lb": lb, "lw": lw, "rb": rb, "rw": rw}):
        assert (lb, lw, rb, rw) == (1, 0, 0, 4)
