from __future__ import annotations

from pathlib import Path

from app.orchestrator.transitions import extract_marked_mermaid, mermaid_from_table


def test_architecture_mermaid_matches_transition_table() -> None:
    root = Path(__file__).resolve().parents[4]
    markdown = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
    marked = extract_marked_mermaid(markdown)
    assert marked == mermaid_from_table()
