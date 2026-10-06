"""Widget goal predicates. Pure; the TypeScript mirror (apps/web/lib/lessons/widgets.ts) runs the
same fixtures. The server re-checks every widget result with these; client results are never
trusted."""

from __future__ import annotations

from typing import Any

from app.lessons.schema import BalanceScaleWidget, FunctionGraphWidget

GRAPH_TOLERANCE = 1e-6


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _balance_state(state: Any) -> tuple[int, int, int, int] | None:
    if not isinstance(state, dict):
        return None
    lb, lw, rb, rw = (state.get(key) for key in ("lb", "lw", "rb", "rw"))
    if not all(_is_int(v) and v >= 0 for v in (lb, lw, rb, rw)):
        return None
    return int(lb), int(lw), int(rb), int(rw)


def _balance_goal(widget: BalanceScaleWidget, state: Any) -> bool:
    parsed = _balance_state(state)
    if parsed is None:
        return False
    lb, lw, rb, rw = parsed
    p = widget.params
    if lb > p.left_boxes or lw > p.left_weights or rb > p.right_boxes or rw > p.right_weights:
        return False  # a state that cannot be reached by taking things away
    balanced = lb * p.box_weight + lw == rb * p.box_weight + rw
    return balanced and (lb, lw, rb) == (1, 0, 0) and rw == p.box_weight


def _graph_goal(widget: FunctionGraphWidget, state: Any) -> bool:
    if not isinstance(state, dict) or not _is_number(state.get("x")):
        return False
    x = float(state["x"])
    g = widget.params
    if not (g.x_min - GRAPH_TOLERANCE <= x <= g.x_max + GRAPH_TOLERANCE):
        return False
    k = round((x - g.x_min) / g.step)
    if abs(g.x_min + k * g.step - x) > GRAPH_TOLERANCE:
        return False
    return abs(g.slope * x + g.intercept - g.target_y) <= GRAPH_TOLERANCE


def goal_met(widget: BalanceScaleWidget | FunctionGraphWidget, state: Any) -> bool:
    if isinstance(widget, BalanceScaleWidget):
        return _balance_goal(widget, state)
    return _graph_goal(widget, state)


def verify_widget_result(
    widget: BalanceScaleWidget | FunctionGraphWidget, result: Any
) -> tuple[bool, str | None]:
    """(ok, rejection code). The client's own opinion of success is not part of the payload."""
    if not isinstance(result, dict) or "final_state" not in result:
        return False, "widget_result_malformed"
    if result.get("widget_id") != widget.widget_id:
        return False, "widget_id_mismatch"
    if not goal_met(widget, result["final_state"]):
        return False, "widget_goal_not_met"
    return True, None
