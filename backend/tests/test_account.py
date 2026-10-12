import server


async def open_session(client, session_id: str, name: str = "Ada", age_confirmed: bool = True):
    response = await client.post(
        "/api/auth/session",
        json={"session_id": session_id, "name": name, "age_confirmed": age_confirmed},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"], body["session_token"]


def _counts():
    return (
        len(server.db.users.docs),
        len(server.db.profiles.docs),
        len(server.db.saves.docs),
        len(server.db.sessions.docs),
    )


async def test_under_17_creates_nothing(client):
    before = _counts()
    refused = await client.post("/api/auth/age", json={"confirmed": False})
    assert refused.status_code == 403
    assert "17" in refused.json()["detail"]
    assert _counts() == before
    headers, user_id, _token = await open_session(client, "session-under-17", age_confirmed=False)
    blocked = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert blocked.status_code == 403
    save = await server.db.saves.find_one({"user_id": user_id})
    assert save is None
    still = await client.post("/api/account/age", headers=headers, json={"confirmed": False})
    assert still.status_code == 403
    assert await server.db.saves.find_one({"user_id": user_id}) is None


async def test_gate_is_not_reshown_once_confirmed(client):
    headers, _user_id, _token = await open_session(client, "session-age-yes", age_confirmed=False)
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["user"]["age_confirmed"] is False
    denied = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert denied.status_code == 403
    confirmed = await client.post("/api/account/age", headers=headers, json={"confirmed": True})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["user"]["age_confirmed"] is True
    again = await client.post("/api/account/age", headers=headers, json={"confirmed": True})
    assert again.status_code == 200
    assert again.json()["user"]["age_confirmed"] is True
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["user"]["age_confirmed"] is True
    created = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert created.status_code == 200, created.text


async def test_delete_soft_deletes_and_kills_the_token(client):
    headers, user_id, token = await open_session(client, "session-delete-me")
    created = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert created.status_code == 200, created.text
    removed = await client.post("/api/account/delete", headers=headers)
    assert removed.status_code == 200, removed.text
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 401
    user = next(doc for doc in server.db.users.docs if doc["user_id"] == user_id)
    profile = next(doc for doc in server.db.profiles.docs if doc["user_id"] == user_id)
    save = next(doc for doc in server.db.saves.docs if doc["user_id"] == user_id)
    session = next(doc for doc in server.db.sessions.docs if doc["session_token"] == token)
    assert user["deleted_at"] is not None
    assert profile["deleted_at"] is not None
    assert save["deleted_at"] is not None
    assert session["deleted_at"] is not None
    assert "_id" not in removed.json()
