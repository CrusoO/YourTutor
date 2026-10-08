"""Rewrite the generated Mermaid block in ARCHITECTURE.md from the transition table."""

from __future__ import annotations

from pathlib import Path

from app.orchestrator.transitions import MARKER_END, MARKER_START, mermaid_from_table

DOC = Path(__file__).resolve().parents[2] / "ARCHITECTURE.md"


def main() -> None:
    raw = DOC.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    start = text.index(MARKER_START) + len(MARKER_START)
    end = text.index(MARKER_END)
    text = text[:start] + "\n" + mermaid_from_table() + "\n" + text[end:]
    DOC.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    print("Mermaid block updated")


if __name__ == "__main__":
    main()
