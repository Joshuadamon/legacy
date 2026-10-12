import server
from server import model_name, model_provider, season_limit


async def open_session(client, session_id: str, name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


def test_model_and_limit_defaults(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    monkeypatch.delenv("LEGACY_SEASON_LIMIT", raising=False)
    assert model_provider() == "anthropic"
    assert model_name() == "claude-sonnet-5"
    assert season_limit() == 60
    monkeypatch.setenv("MODEL_PROVIDER", "anthropic")
    monkeypatch.setenv("MODEL_NAME", "claude-test")
    monkeypatch.setenv("LEGACY_SEASON_LIMIT", "12")
    assert model_provider() == "anthropic"
    assert model_name() == "claude-test"
    assert season_limit() == 12


async def test_register_login_link_and_name_session(client):
    registered = await client.post(
        "/api/auth/register",
        json={"email": "Ada@Example.com", "password": "correct-horse", "name": "Ada"},
    )
    assert registered.status_code == 200, registered.text
    body = registered.json()
    assert body["session_token"]
    assert body["user"]["email"] == "ada@example.com"
    assert "password_hash" not in body["user"]
    assert "_id" not in body["user"]
    stored = next(doc for doc in server.db.users.docs if doc["user_id"] == body["user"]["user_id"])
    assert stored["password_hash"] != "correct-horse"
    assert stored["password_hash"].startswith("$2")
    headers = {"Authorization": f"Bearer {body['session_token']}"}
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    wrong = await client.post("/api/auth/login", json={"email": "ada@example.com", "password": "nope-nope"})
    assert wrong.status_code == 401
    logged = await client.post("/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse"})
    assert logged.status_code == 200, logged.text
    assert logged.json()["user"]["user_id"] == body["user"]["user_id"]
    name_headers, name_id = await open_session(client, "session-name-still-works", "Lin")
    state = await client.get("/api/game/state", headers=name_headers)
    assert state.status_code == 200
    created = await client.post("/api/game/new", headers=name_headers, json={"name": "Lin", "background_key": "stable"})
    assert created.status_code == 200, created.text
    linked = await client.post(
        "/api/auth/link-email",
        headers=name_headers,
        json={"email": "lin@example.com", "password": "another-secret"},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["user"]["user_id"] == name_id
    assert linked.json()["user"]["email"] == "lin@example.com"
    assert "password_hash" not in linked.json()["user"]
    via_email = await client.post(
        "/api/auth/login",
        json={"email": "lin@example.com", "password": "another-secret"},
    )
    assert via_email.status_code == 200
    assert via_email.json()["user"]["user_id"] == name_id
    again = await client.post(
        "/api/auth/link-email",
        headers=name_headers,
        json={"email": "other@example.com", "password": "another-secret"},
    )
    assert again.status_code == 409


async def test_season_limit_returns_429(client, monkeypatch):
    monkeypatch.setenv("LEGACY_SEASON_LIMIT", "2")
    headers, _user_id = await open_session(client, "session-rate-limit")
    created = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert created.status_code == 200, created.text
    first = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert first.status_code == 200, first.text
    second = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert second.status_code == 200, second.text
    age = second.json()["save"]["character"]["age_quarters"]
    blocked = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert blocked.status_code == 429
    assert "limited" in blocked.json()["detail"].lower()
    state = await client.get("/api/game/state", headers=headers)
    assert state.status_code == 200
    assert state.json()["save"]["alive"] is True
    assert state.json()["save"]["character"]["age_quarters"] == age
