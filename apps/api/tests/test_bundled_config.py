"""`apps/api/bundled_config` must equal `config/` (Vercel deploys only apps/api; see paths.py)."""

from __future__ import annotations

from pathlib import Path

from app.registries.paths import bundled_config_dir, config_dir

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
