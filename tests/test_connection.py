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
