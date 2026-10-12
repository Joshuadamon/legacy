import server


async def test_skip_advances_three_quiet_years_with_a_mild_montage(client):
    headers, _user_id = await open_session(client)
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    start = created.json()["save"]["character"]
    start_age = int(start["age_years"])
    before = dict(start["stats"])

    skipped = await client.post("/api/game/skip", headers=headers)
    assert skipped.status_code == 200, skipped.text
    body = skipped.json()
    assert body["years_skipped"] == 3
    assert body["new_age"] == start_age + 3
    assert body["save"]["alive"] is True
    assert body["save"]["character"]["age_years"] == start_age + 3
    assert body["save"]["current_event"]["title"]
    assert len(body["save"]["current_event"]["choices"]) >= 2
    assert "_id" not in body
    assert "_id" not in body["save"]

    montage = body["montage"]
    text = montage["text"] if isinstance(montage, dict) else montage
    assert isinstance(text, str) and text.strip()
    lines = montage["lines"] if isinstance(montage, dict) else text.splitlines()
    assert len(lines) == 3
    for age in range(start_age + 1, start_age + 4):
        assert str(age) in text

    meters = ("health", "happiness", "smarts", "looks", "reputation", "family")
    for key in meters:
        assert abs(int(body["stat_changes"][key])) <= 8
        assert body["save"]["character"]["stats"][key] == before[key] + body["stat_changes"][key]
    assert abs(int(body["stat_changes"]["money"])) <= 40

    again = await client.post("/api/game/skip", headers=headers)
    assert again.status_code == 200, again.text
    assert again.json()["years_skipped"] == 3
    assert again.json()["new_age"] == start_age + 6


async def test_skip_pays_wages_and_compounds_a_shop_without_a_work_event(client):
    headers, user_id = await open_session(client, "session-skip-work-01")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = stored["character"]
    character["age_years"] = 30
    character["career"] = {"title": "Clerk", "field": "service", "level": 1, "income": 240}
    character["business"] = {"name": "Salt Line", "type": "bakery", "value": 500}
    character["work_chapter"] = "settled"
    money = int(character["stats"]["money"])
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character}},
    )

    skipped = await client.post("/api/game/skip", headers=headers)
    assert skipped.status_code == 200, skipped.text
    body = skipped.json()
    assert body["years_skipped"] == 3
    assert body["new_age"] == 33
    assert 240 * 3 - 30 <= body["stat_changes"]["money"] <= 240 * 3 + 30
    assert body["save"]["character"]["stats"]["money"] == money + body["stat_changes"]["money"]
    career = body["save"]["character"]["career"]
    assert career["level"] == 1
    assert career["income"] == 240
    assert body["save"]["character"]["business"]["value"] == 561
    assert body["save"]["character"]["business"]["value"] > 100


async def test_skip_stops_when_health_fails_mid_montage(client):
    headers, user_id = await open_session(client, "session-skip-health")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = stored["character"]
    character["age_years"] = 90
    character["stats"]["health"] = 2
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character}},
    )

    skipped = await client.post("/api/game/skip", headers=headers)
    assert skipped.status_code == 200, skipped.text
    body = skipped.json()
    assert body["years_skipped"] == 1
    assert body["save"]["alive"] is False
    assert body["new_age"] == body["save"]["character"]["age_years"]
    assert body["new_age"] == 91
    assert body["save"]["character"]["age_years"] == 91
    assert body["save"]["current_event"] is None
    assert body["save"]["cause_of_death"]
    assert int(body["save"]["marks_earned"]) > 0
    assert "_id" not in body["save"]
    text = body["montage"]["text"] if isinstance(body["montage"], dict) else body["montage"]
    assert "91" in text


async def test_skip_stops_on_hunter_death(client):
    headers, user_id = await open_session(client, "session-skip-hunter")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Eve", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = stored["character"]
    character["age_years"] = 30
    character["stats"]["health"] = 80
    character["species"] = "vampire"
    character["species_data"] = {
        "clan": "Ash Court",
        "bloodlust": 100,
        "masquerade": 70,
        "last_power_age": None,
    }
    character["hunter_heat"] = 90
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character}},
    )

    skipped = await client.post("/api/game/skip", headers=headers)
    assert skipped.status_code == 200, skipped.text
    body = skipped.json()
    assert body["years_skipped"] == 1
    assert body["new_age"] == 31
    assert body["save"]["alive"] is False
    assert body["save"]["true_death"] is True
    assert body["save"]["character"]["age_years"] == 31
    assert body["save"]["current_event"] is None
    assert "Hunters" in body["save"]["cause_of_death"]
    assert "_id" not in body["save"]
    assert "deleted_at" not in body["save"]
    kept = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    assert kept is not None
    assert kept["alive"] is False


async def test_skip_rejected_on_a_dead_save(client):
    headers, user_id = await open_session(client, "session-skip-dead")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    age = created.json()["save"]["character"]["age_years"]
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"alive": False, "cause_of_death": "Already gone."}},
    )

    skipped = await client.post("/api/game/skip", headers=headers)
    assert skipped.status_code == 409
    assert "over" in skipped.json()["detail"].lower()
    state = await client.get("/api/game/state", headers=headers)
    assert state.status_code == 200
    assert state.json()["save"]["alive"] is False
    assert state.json()["save"]["character"]["age_years"] == age


async def test_skip_rejected_on_a_fatal_year_and_at_end_of_life(client):
    headers, user_id = await open_session(client, "session-skip-fatal")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    await _replace_event(
        user_id,
        {
            "title": "The end",
            "narrative": "It is time.",
            "choices": [
                {"label": "Let go", "outcome": "The light goes ordinary.", "effects": {}, "flags": {}, "fatal": True},
                {"label": "Hold", "outcome": "Not yet.", "effects": {}, "flags": {}},
            ],
        },
        age=40,
    )
    blocked = await client.post("/api/game/skip", headers=headers)
    assert blocked.status_code == 409
    assert "skip" in blocked.json()["detail"].lower()
    state = await client.get("/api/game/state", headers=headers)
    assert state.json()["save"]["alive"] is True
    assert state.json()["save"]["character"]["age_years"] == 40

    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = stored["character"]
    character["age_years"] = 100
    character["stats"]["health"] = 40
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character, "current_event": state.json()["save"]["current_event"]}},
    )
    # The fatal event is still current; replace it with a quiet year so only age blocks the skip.
    await _replace_event(
        user_id,
        {
            "title": "A narrow winter",
            "narrative": "The house is quiet.",
            "choices": [
                {"label": "Stay in", "outcome": "You do.", "effects": {}, "flags": {}},
                {"label": "Step out", "outcome": "The cold is brief.", "effects": {}, "flags": {}},
            ],
        },
    )
    ended = await client.post("/api/game/skip", headers=headers)
    assert ended.status_code == 409
    assert "end" in ended.json()["detail"].lower()
    still = await client.get("/api/game/state", headers=headers)
    assert still.json()["save"]["alive"] is True
    assert still.json()["save"]["character"]["age_years"] == 100


async def open_session(client, session_id: str = "session-skip-0001", name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def _replace_event(user_id: str, event: dict, age: int | None = None) -> None:
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    update = {"current_event": event}
    if age is not None:
        stored["character"]["age_years"] = age
        stored["character"]["stage"] = "adult"
        update["character"] = stored["character"]
    await server.db.saves.update_one({"user_id": user_id, "deleted_at": None}, {"$set": update})
