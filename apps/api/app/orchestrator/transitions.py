"""Single normative transition table. Mermaid is generated from this list."""

from __future__ import annotations

from dataclasses import dataclass

MARKER_START = "<!-- ORCH_TRANSITIONS:START -->"
MARKER_END = "<!-- ORCH_TRANSITIONS:END -->"


@dataclass(frozen=True)
class Transition:
    rule_id: str
    state_before: str
    event: str
    state_after: str
    action: str
    label: str


TRANSITIONS: tuple[Transition, ...] = (
    Transition("R01", "start", "start", "predict", "predict", "new skill"),
    Transition("R02", "start", "start", "practice", "show_item", "introduced skill"),
    Transition("R03", "start", "start", "warmup", "warmup_item", "FSRS due"),
    Transition("R04", "predict", "predict_response", "worked_example", "worked_example", "advance"),
    Transition("R05", "worked_example", "continue", "practice", "show_item", "begin practice"),
    Transition("R06", "practice", "request_help", "practice", "hint", "hint 1 or 2"),
    Transition("R07", "practice", "answer", "practice", "hint", "wrong before hint 2"),
    Transition(
        "R08", "practice", "answer", "explain_back", "explain_back_prompt", "first unhinted"
    ),
    Transition("R09", "practice", "answer", "reveal", "reveal_solution", "wrong after hint 2"),
    Transition("R10", "practice", "show_solution", "reveal", "reveal_solution", "after two hints"),
    Transition("R11", "reveal", "continue", "practice", "similar_item", "same skill and tier"),
    Transition("R12", "reveal", "continue", "start", "content_gap", "no other item"),
    Transition("R13", "explain_back", "continue", "practice", "show_item", "skip explain"),
    Transition(
        "R14", "explain_back", "explain_back", "select_skill", "explain_back_result", "store text"
    ),
    Transition("R15", "practice", "idle_nudge", "practice", "nudge", "no pedagogy change"),
    Transition("R16", "any", "consent_revoked", "ended", "end_session", "consent revoked"),
    Transition("R17", "any", "idle", "ended", "end_session", "10 min idle"),
    Transition("R18", "start", "start", "ended", "end_session", "soft or hard cap"),
    Transition("R19", "diagnostic", "answer", "diagnostic", "show_item", "next item"),
    Transition("R20", "diagnostic", "answer", "ended", "end_session", "seed mastery"),
    Transition("R21", "checkpoint", "answer", "ended", "checkpoint_score", "no mastery write"),
    Transition("R22", "practice", "show_solution", "practice", "show_item", "illegal reveal"),
    Transition("R31", "practice", "answer", "practice", "check_your_work", "slip"),
    Transition("R32", "practice", "request_help", "stuck", "ask_stuck_point", "first help"),
    Transition("R32", "stuck", "stuck_choice", "practice", "hint", "start or restate"),
    Transition("R32", "stuck", "stuck_choice", "stuck_step", "ask_stuck_step", "at a step"),
    Transition("R32", "stuck", "stuck_choice", "practice", "show_item", "might be right"),
    Transition("R32", "stuck", "stuck_choice", "practice", "check_your_work", "recheck"),
    Transition("R32", "stuck_step", "stuck_step", "practice", "hint", "step hint"),
    Transition("R33", "practice", "answer", "probe", "show_item", "prerequisite probe"),
    Transition("R33", "practice", "answer", "representation", "worked_example", "new view"),
    Transition("R33", "probe", "answer", "representation", "worked_example", "probe right"),
    Transition("R33", "probe", "answer", "practice", "show_item", "probe wrong"),
    Transition("R33", "representation", "continue", "practice", "show_item", "back to T"),
)


def mermaid_from_table() -> str:
    lines = ["```mermaid", "stateDiagram-v2"]
    for row in TRANSITIONS:
        lines.append(
            f"  {row.state_before} --> {row.state_after}: {row.event}/{row.action} ({row.rule_id})"
        )
    lines.append("```")
    return "\n".join(lines)


def rule_id_for(state_before: str, event: str, action: str) -> str:
    for row in TRANSITIONS:
        if (
            row.state_before in {state_before, "any"}
            and row.event == event
            and row.action == action
        ):
            return row.rule_id
    return f"{state_before}:{event}->{action}"


def extract_marked_mermaid(markdown: str) -> str:
    start = markdown.find(MARKER_START)
    end = markdown.find(MARKER_END)
    if start < 0 or end < 0 or end <= start:
        return ""
    return markdown[start + len(MARKER_START) : end].strip()
