from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from tests.conftest import World, auth_header


def test_research_routes_404_when_module_off(client: TestClient, world: World) -> None:
    previous = settings.research_module
    try:
        settings.research_module = False
        denied = client.get("/analytics/export", headers=auth_header(world.admin_token))
        assert denied.status_code == 404
    finally:
        settings.research_module = previous
