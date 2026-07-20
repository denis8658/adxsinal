import httpx
import pytest
from datetime import UTC, datetime, timedelta
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.pocketoption_client import PocketOptionClient


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", engine_loop_interval_ms=20, engine_mode="signal_only")


@pytest.fixture
def external_transport():
    async def handler(request: httpx.Request):
        path = request.url.path
        if path == "/api/connection-stats": return httpx.Response(200, json={"connected": True})
        if path == "/api/balance": return httpx.Response(200, json={"balance": 1000, "currency": "USD", "account_type": "demo"})
        if path == "/api/assets": return httpx.Response(200, json={"assets": ["EURUSD_otc"]})
        if path == "/api/candles":
            assert request.method == "POST"
            now = datetime.now(UTC)
            candles = []
            for i in range(80):
                close = 1 + i * .001 + ((i % 5) - 2) * .0001
                candles.append({"timestamp": (now - timedelta(seconds=(79-i)*5)).isoformat(), "open": close-.0002, "high": close+.0005, "low": close-.0005, "close": close})
            return httpx.Response(200, json=candles)
        return httpx.Response(200, json={"success": True})
    return httpx.MockTransport(handler)


@pytest.fixture
def client(settings, external_transport):
    external = PocketOptionClient("https://example.test", transport=external_transport)
    with TestClient(create_app(settings, client=external)) as value:
        yield value


@pytest.fixture
def session_id(client):
    response = client.post("/api/v1/connection/session", json={"ssid": '42["auth",{"session":"long-secret-session"}]'})
    assert response.status_code == 201, response.text
    return response.json()["session_id"]
