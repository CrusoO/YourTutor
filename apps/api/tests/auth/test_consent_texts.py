"""Consent wording files: the manifest matches, one changed byte fails, new scopes are complete."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.auth import consent_texts as ct
from app.auth.scopes import NEW_SCOPES, SCOPE_REGISTRY

WITH_TEXT = sorted({s.text_scope for s in SCOPE_REGISTRY.values() if s.text_scope})


@pytest.fixture
def copy_of_texts(tmp_path: Path) -> Path:
    target = tmp_path / "consent_texts"
    shutil.copytree(ct.texts_root(), target)
    return target


def test_the_committed_manifest_matches_the_files() -> None:
    assert ct.verify() == []


def test_one_changed_byte_fails_verification(copy_of_texts: Path) -> None:
    assert ct.verify(copy_of_texts) == []
    path = copy_of_texts / "math_check" / "v1.en.guardian.md"
    path.write_bytes(path.read_bytes().replace(b"short", b"shorT"))
    assert any("hash differs" in p for p in ct.verify(copy_of_texts))


def test_an_unlisted_or_missing_file_fails_verification(copy_of_texts: Path) -> None:
    (copy_of_texts / "math_check" / "v2.en.child.md").write_text("new\n", encoding="utf-8")
    assert any("not in manifest" in p for p in ct.verify(copy_of_texts))
    (copy_of_texts / "math_check" / "v2.en.child.md").unlink()
    (copy_of_texts / "photo_check" / "v1.en.child.md").unlink()
    assert any("no file" in p for p in ct.verify(copy_of_texts))
    (copy_of_texts / ct.MANIFEST_NAME).unlink()
    assert ct.verify(copy_of_texts)


def test_crlf_and_lf_files_hash_the_same(tmp_path: Path) -> None:
    lf, crlf = tmp_path / "a.md", tmp_path / "b.md"
    lf.write_bytes(b"one\ntwo\n")
    crlf.write_bytes(b"one\r\ntwo\r\n")
    assert ct.file_sha256(lf) == ct.file_sha256(crlf)


def test_the_manifest_command_regenerates_the_same_file(copy_of_texts: Path) -> None:
    before = (copy_of_texts / ct.MANIFEST_NAME).read_bytes()
    ct.write_manifest(copy_of_texts)
    assert (copy_of_texts / ct.MANIFEST_NAME).read_bytes() == before
    assert b"\r" not in before


@pytest.mark.parametrize("scope", sorted(NEW_SCOPES | {"learning_profile"}))
def test_every_new_scope_has_guardian_and_child_text(scope: str) -> None:
    assert SCOPE_REGISTRY[scope].text_scope == scope
    for audience in ct.AUDIENCES:
        path = ct.texts_root() / scope / f"v1.en.{audience}.md"
        assert path.read_text(encoding="utf-8").strip(), path
    manifest = ct.current_manifest(scope)
    assert manifest and manifest["version"] == "v1"
    assert set(manifest["sha256"]) == set(ct.AUDIENCES)


def test_a_scope_with_missing_or_tampered_text_has_no_current_manifest(
    copy_of_texts: Path,
) -> None:
    assert ct.current_manifest("photo_check", root=copy_of_texts)
    (copy_of_texts / "photo_check" / "v1.en.child.md").write_text("changed\n", encoding="utf-8")
    assert ct.current_manifest("photo_check", root=copy_of_texts) is None
    assert ct.current_manifest("tutoring", root=copy_of_texts) is None


def test_every_scope_has_a_flag_and_a_deletion_handler() -> None:
    for scope in SCOPE_REGISTRY.values():
        if scope.id not in ("tutoring", "free_text", "uploads"):
            assert scope.flag_setting and scope.deletion_handler_id, scope.id
    for scope_id in WITH_TEXT:
        assert SCOPE_REGISTRY[scope_id].guardian_only


def test_the_loader_imports_only_the_standard_library() -> None:
    source = Path(ct.__file__).read_text(encoding="utf-8")
    imports = [ln for ln in source.splitlines() if ln.startswith(("import ", "from "))]
    assert not [ln for ln in imports if "app." in ln or "sqlalchemy" in ln or "fastapi" in ln]
