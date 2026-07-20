from unittest.mock import AsyncMock

import pytest


def test_invalid_ssid(client):
    response = client.post("/api/v1/connection/session", json={"ssid": "short"})
    assert response.status_code == 422


def test_session_never_returns_ssid(client):
    secret = '42["auth",{"session":"very-secret-value"}]'
    response = client.post("/api/v1/connection/session", json={"ssid": secret})
    assert response.status_code == 201
    assert secret not in response.text and "ssid" not in response.json()


def test_disconnect(client, session_id):
    response = client.delete(f"/api/v1/connection/session/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"


def test_create_is_idempotent_while_session_is_active(client):
    payload = {"ssid": '42["auth",{"session":"idempotent-secret"}]'}

    first = client.post("/api/v1/connection/session", json=payload)
    second = client.post("/api/v1/connection/session", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["session_id"] == first.json()["session_id"]


def test_reconnect_reuses_persisted_session(client):
    payload = {"ssid": '42["auth",{"session":"reconnect-secret"}]'}

    first = client.post("/api/v1/connection/session", json=payload)
    session_id = first.json()["session_id"]
    disconnected = client.delete(f"/api/v1/connection/session/{session_id}")
    second = client.post("/api/v1/connection/session", json=payload)

    assert first.status_code == 201
    assert disconnected.status_code == 200
    assert second.status_code == 201
    assert second.json()["session_id"] == session_id
    assert client.get(f"/api/v1/account/{session_id}").status_code == 200


def test_connection_accepts_external_api_contract_and_preserves_real_mode(client):
    service = client.app.state.connections
    service.client.connection_stats = AsyncMock(return_value={"total_connections": 1, "is_demo": False})
    service.client.balance = AsyncMock(return_value={"balance": 250, "currency": "USD", "account_type": "real"})

    response = client.post(
        "/api/v1/connection/session",
        json={"ssid": '42["auth",{"session":"real-account-contract"}]'},
    )

    assert response.status_code == 201
    assert response.json()["external_api_connected"] is True
    assert response.json()["account_mode"] == "real"


def test_persistence_failure_does_not_leave_orphan_in_memory(client):
    payload = {"ssid": '42["auth",{"session":"database-failure-secret"}]'}
    service = client.app.state.connections
    original_upsert = service.repo.upsert_session
    service.repo.upsert_session = AsyncMock(side_effect=RuntimeError("database unavailable"))

    with pytest.raises(RuntimeError, match="database unavailable"):
        client.post("/api/v1/connection/session", json=payload)
    assert service._sessions == {}

    service.repo.upsert_session = original_upsert
    retried = client.post("/api/v1/connection/session", json=payload)

    assert retried.status_code == 201
