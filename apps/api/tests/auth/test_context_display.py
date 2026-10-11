"""UI-1: the setup conversation shows every known class and a name for each curriculum."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.registries.loaders import load_curriculum


def test_context_options_list_every_known_grade_so_empty_ones_can_say_coming_soon(
    client: TestClient,
) -> None:
    data = client.get("/context/options").json()
    assert data["grades"] == list(range(1, 13))  # from config/grade_bands.yaml, not from code
    with_content = {g["grade"] for c in data["curricula"] for g in c["grades"]}
    assert with_content and with_content < set(data["grades"])


def test_each_curriculum_carries_its_optional_display_titles(client: TestClient) -> None:
    data = client.get("/context/options").json()
    for curriculum in data["curricula"]:
        assert isinstance(curriculum["titles"], dict)


def test_a_curriculum_can_name_itself_per_language(tmp_path: Path) -> None:
    folder = tmp_path / "demo_board"
    folder.mkdir()
    (folder / "curriculum.yaml").write_text(
        "id: demo_board\n"
        "default_timezone: UTC\n"
        "jurisdiction_profile: default_strict\n"
        'titles: {en: "Demo board", hi: "डेमो"}\n'
        "books: []\n",
        encoding="utf-8",
    )
    spec = load_curriculum("demo_board", root=tmp_path)
    assert spec.titles == {"en": "Demo board", "hi": "डेमो"}


def test_today_says_whether_the_student_is_a_guest(client: TestClient) -> None:
    from tests.conftest import auth_header

    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    body = client.get("/students/me/today", headers=auth_header(guest["token"])).json()
    assert body["guest"] is True


def test_a_family_student_is_not_a_guest(client: TestClient, world) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import auth_header

    body = client.get("/students/me/today", headers=auth_header(world.student_token)).json()
    assert body["guest"] is False
