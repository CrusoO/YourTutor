"""No command may print book text. The fixture book holds a recognisable run of words."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.bookcheck.cli import main
from app.bookcheck.settings import BOOKS_ENV, OUT_ENV
from tests.bookcheck.conftest import BOOK_PAGES, BOOK_RUN, item, write_book, write_drafts

LEAKS = ["zephyrine", "quotient", "Newton studied", "Balanced and unbalanced", "Force and Laws"]


def test_no_command_prints_book_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    content: Path,
) -> None:
    from app.bookcheck.settings import Settings

    settings = Settings(tmp_path / "books", tmp_path / "out", None)
    monkeypatch.setenv(BOOKS_ENV, str(settings.books_dir))
    monkeypatch.setenv(OUT_ENV, str(settings.out_dir))
    write_drafts(
        content,
        [
            item(
                "speed_and_velocity",
                "What is average speed of a cyclist?",
                "distance divided by time",
            ),
            item("speed_and_velocity", "stem", "a", expl=" ".join(BOOK_RUN.split()[:9])),
        ],
    )
    root = ["--content-root", str(content)]
    codes = {}
    for command in (["init"], ["ingest"]):
        codes[command[0]] = main(command)
        assert "zephyrine" not in capsys.readouterr().out
    write_book(settings)  # after ingest, which rebuilds the manifest from the (empty) books folder
    monkeypatch.setattr(
        "app.bookcheck.ingest.ingest", lambda s: {"pdfs": 0, "new": 0, "skipped": 0}
    )
    commands = [
        ["toc"],
        ["facts"],
        ["coverage", "--class", "9", "--subject", "physics", *root],
        ["check", "--class", "9", "--subject", "physics", *root],
        ["overlap", "--class", "9", "--subject", "physics", *root],
        ["overlap", *root],
        ["report"],
        ["run-all", "--class", "9", *root],
    ]
    for command in commands:
        codes[command[0]] = main(command)
        captured = capsys.readouterr()
        shown = captured.out + captured.err
        for leak in LEAKS + [w for line in BOOK_PAGES for w in [line.splitlines()[-1]]]:
            assert leak not in shown, f"{command[0]} printed book text"
    assert codes["overlap"] == 1  # the copied run is found, so the exit code gates
    assert (settings.out_dir / "report.md").is_file()
    assert "zephyrine" in (settings.out_dir / "overlap" / "9-physics.jsonl").read_text("utf-8")
