"""requirements.txt and pyproject.toml must list the same libraries.

Vercel installs the API's libraries from pyproject.toml when it has a [project] table and ignores
requirements.txt then; Docker and CI use requirements.txt. A list that is missing or different in
one place means a deployed API without FastAPI ("No module named 'fastapi'"), as happened once.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

API = Path(__file__).resolve().parents[1]


def _requirements() -> list[str]:
    lines = (API / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def _pyproject() -> list[str]:
    data = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))
    return list(data["project"]["dependencies"])


def test_pyproject_lists_the_same_dependencies_as_requirements_txt() -> None:
    assert sorted(_pyproject()) == sorted(_requirements())


def test_the_list_is_not_empty_and_names_the_web_framework() -> None:
    names = {
        entry.split("[")[0].split(">")[0].split("=")[0].split("<")[0].strip()
        for entry in _pyproject()
    }
    assert {"fastapi", "sqlalchemy", "psycopg", "pydantic-settings"} <= names
