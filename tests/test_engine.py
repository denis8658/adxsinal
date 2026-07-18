import time


def payload(session_id, **updates):
    value = {"session_id": session_id, "asset": "EURUSD_otc", "timeframe_seconds": 5, "expiration_seconds": 30, "amount": 1, "profile": "balanced", "auto_execute": False, "account_mode": "demo"}
    value.update(updates); return value


def test_key_required(client, session_id):
    assert client.post("/api/v1/engine/start", json=payload(session_id)).status_code == 401


def test_start_duplicate_and_stop(client, session_id):
    headers = {"X-Engine-Key": "test-secret-key"}
    first = client.post("/api/v1/engine/start", headers=headers, json=payload(session_id))
    assert first.status_code == 202, first.text
    assert client.post("/api/v1/engine/start", headers=headers, json=payload(session_id)).status_code == 409
    engine_id = first.json()["engine_id"]
    stopped = client.post("/api/v1/engine/stop", headers=headers, json={"engine_id": engine_id})
    assert stopped.status_code == 200


def test_real_account_is_blocked(client, session_id):
    response = client.post("/api/v1/engine/start", headers={"X-Engine-Key": "test-secret-key"}, json=payload(session_id, account_mode="real"))
    assert response.status_code == 403


def test_pause_resume_and_signal_only_worker(client, session_id):
    headers = {"X-Engine-Key": "test-secret-key"}
    started = client.post("/api/v1/engine/start", headers=headers, json=payload(session_id))
    engine_id = started.json()["engine_id"]
    assert client.post("/api/v1/engine/pause", headers=headers, json={"engine_id": engine_id}).json()["status"] == "paused"
    assert client.post("/api/v1/engine/resume", headers=headers, json={"engine_id": engine_id}).json()["status"] == "running"
    time.sleep(.15)
    status = client.get(f"/api/v1/engine/status/{engine_id}").json()
    assert status["orders_executed"] == 0
    assert status["status"] in {"RUNNING", "ERROR"}
    client.post("/api/v1/engine/stop", headers=headers, json={"engine_id": engine_id})
