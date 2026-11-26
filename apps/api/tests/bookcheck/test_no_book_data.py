"""Guards: book PDFs and the private output folder can never be committed, and the tool refuses
folders inside the repository."""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from app.bookcheck.cli import main
from app.bookcheck.settings import (
    BOOKS_ENV,
    OUT_ENV,
    Settings,
    SettingsError,
    find_repo_root,
    load_settings,
)

REPO = find_repo_root()
API = Path(__file__).resolve().parents[2]


def test_git_tracks_no_pdf() -> None:
    if shutil.which("git") is None or REPO is None:
        pytest.skip("git is not available, cannot list tracked files")
    done = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        pytest.skip("git ls-files failed here")
    pdfs = [name for name in done.stdout.splitlines() if name.lower().endswith(".pdf")]
    assert not pdfs, f"{len(pdfs)} PDF file(s) are tracked by git; remove them from the index"


def test_gitignore_blocks_pdfs_and_the_private_folders() -> None:
    assert REPO is not None
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    for entry in ("private-books/", "private-books-out/", "apps/api/**/*.pdf", "content/**/*.pdf"):
        assert entry in lines


def test_books_dir_inside_the_repo_is_refused(tmp_path: Path) -> None:
    assert REPO is not None
    inside = Settings(REPO / "private-books", tmp_path / "out", REPO)
    with pytest.raises(SettingsError):
        inside.check()
    inside_out = Settings(tmp_path / "books", REPO / "content" / "out", REPO)
    with pytest.raises(SettingsError):
        inside_out.check()


def test_folders_may_not_contain_each_other(tmp_path: Path) -> None:
    with pytest.raises(SettingsError):
        Settings(tmp_path / "a", tmp_path / "a" / "b", None).check()


def test_onedrive_path_only_warns(tmp_path: Path) -> None:
    warnings = Settings(tmp_path / "OneDrive" / "books", tmp_path / "out", None).check()
    assert warnings and "OneDrive" in warnings[0]


def test_cli_refuses_a_repo_folder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert REPO is not None
    monkeypatch.setenv(BOOKS_ENV, str(REPO / "private-books"))
    monkeypatch.setenv(OUT_ENV, str(REPO.parent / "private-out-ok"))
    assert main(["init"]) == 2
    assert "inside the git repository" in capsys.readouterr().err
    assert not (REPO / "private-books").exists()


def test_load_settings_reads_the_environment(tmp_path: Path) -> None:
    got = load_settings({BOOKS_ENV: str(tmp_path / "b"), OUT_ENV: str(tmp_path / "o")})
    assert got.books_dir == tmp_path / "b" and got.out_dir == tmp_path / "o"


def test_pypdf_is_an_optional_extra_only() -> None:
    data = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))
    assert "pypdf" not in " ".join(data["project"]["dependencies"])
    assert any("pypdf" in d for d in data["project"]["optional-dependencies"]["bookcheck"])
    assert "pypdf" not in (API / "requirements.txt").read_text(encoding="utf-8")
