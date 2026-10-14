import server
from test_api import open_session


async def test_activities_require_a_session(client):
    response = await client.get("/api/activities")
    assert response.status_code == 401
    refused = await client.post("/api/activities/perform", json={"activity_id": "rest"})
    assert refused.status_code == 401


async def test_activities_lists_fifteen_for_a_signed_in_life(client):
    headers, _user_id = await open_session(client, "session-act-0001")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    listed = await client.get("/api/activities", headers=headers)
    assert listed.status_code == 200, listed.text
    activities = listed.json()["activities"]
    assert len(activities) == 15
    assert len({item["id"] for item in activities}) == 15
    assert {item["category"] for item in activities} <= {"risk", "social", "health", "lifestyle"}
    rest = next(item for item in activities if item["id"] == "rest")
    assert rest["available"] is True
    wager = next(item for item in activities if item["id"] == "wager")
    assert wager["available"] is False
    assert wager["locked_reason"]


async def test_perform_activity_changes_the_body_and_not_the_year(client):
    headers, user_id = await open_session(client, "session-act-0002")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    before = created.json()["save"]["character"]
    performed = await client.post("/api/activities/perform", headers=headers, json={"activity_id": "rest"})
    assert performed.status_code == 200, performed.text
    body = performed.json()
    assert body["activity"]["title"]
    assert body["activity"]["narrative"]
    assert body["activity"]["outcome"]
    assert body["deltas"]["stats"]["health"] == 2
    assert body["deltas"]["stats"]["happiness"] == 3
    assert body["deltas"]["money"] == 0
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    assert stored["character"]["age_quarters"] == before["age_quarters"]
    assert stored["character"]["stats"]["health"] == before["stats"]["health"] + 2
    locked = await client.post("/api/activities/perform", headers=headers, json={"activity_id": "wager"})
    assert locked.status_code == 403
    missing = await client.post("/api/activities/perform", headers=headers, json={"activity_id": "no-such"})
    assert missing.status_code == 400
