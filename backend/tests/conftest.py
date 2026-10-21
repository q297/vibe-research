import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.services.registry import get_services

USERS = {
    u["username"]: u
    for u in json.loads(
        (Path(__file__).parents[1] / "app/stubs/fixtures/users.json").read_text(encoding="utf-8")
    )
}


@pytest.fixture(autouse=True)
def fast_stubs(monkeypatch):
    monkeypatch.setenv("STUB_STEP_DELAY_S", "0")
    get_settings.cache_clear()
    get_services.cache_clear()
    yield
    get_settings.cache_clear()
    get_services.cache_clear()


@pytest.fixture
async def client():
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def login(client):
    async def _login(username: str) -> dict[str, str]:
        user = USERS[username]
        resp = await client.post(
            "/v1/auth/login", json={"username": username, "password": user["password"]}
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login
