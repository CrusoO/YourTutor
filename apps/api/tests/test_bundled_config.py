"""`apps/api/bundled_config` must equal `config/` (Vercel deploys only apps/api; see paths.py)."""

from __future__ import annotations

from pathlib import Path

from app.registries.paths import (
    bundled_config_dir,
    bundled_curricula_dir,
    config_dir,
    content_curricula_dir,
)

SOURCE = Path(__file__).resolve().parents[3] / "config"


def _files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_the_bundled_copy_matches_the_config_folder() -> None:
    assert _files(bundled_config_dir()) == _files(SOURCE), (
        "run: python scripts/sync_bundled_config.py"
    )


def test_without_the_repo_config_folder_the_bundled_copy_is_used(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("CONFIG_DIR", raising=False)
    monkeypatch.setattr("app.registries.paths.repo_root", lambda: tmp_path)
    assert config_dir() == bundled_config_dir()
    assert (config_dir() / "limits.yaml").is_file()


def test_the_bundled_curricula_match_the_content_folder() -> None:
    source = SOURCE.parent / "content" / "curricula"
    hint = "run: python scripts/sync_bundled_config.py"
    assert _files(bundled_curricula_dir()) == _files(source), hint


def test_without_the_content_folder_the_bundled_curricula_are_used(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONTENT_DIR", str(tmp_path))
    assert content_curricula_dir() == bundled_curricula_dir()
    assert (content_curricula_dir() / "cbse" / "curriculum.yaml").is_file()
