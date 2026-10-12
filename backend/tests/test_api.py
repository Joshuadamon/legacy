import server


async def open_session(client, session_id: str = "session-ada-0001", name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] == "true"


async def test_session_is_one_time_and_logout_kills_it(client):
    headers, _user_id = await open_session(client)
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["name"] == "Ada"
    again = await client.post("/api/auth/session", json={"session_id": "session-ada-0001", "name": "Ada"})
    assert again.status_code == 401
    logged_out = await client.post("/api/auth/logout", headers=headers)
    assert logged_out.status_code == 200
    rejected = await client.get("/api/auth/me", headers=headers)
    assert rejected.status_code == 401


async def test_new_life_ages_one_quarter_per_choice(client):
    headers, _user_id = await open_session(client, "session-life-0001")
    profile = await client.get("/api/profile", headers=headers)
    assert profile.json()["profile"]["marks"] == 250
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200, created.text
    save = created.json()["save"]
    assert save["character"]["age_years"] == 0
    assert save["character"]["species"] == "human"
    assert save["alive"] is True
    assert len(save["current_event"]["choices"]) >= 2
    advanced = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert advanced.status_code == 200, advanced.text
    nxt = advanced.json()["save"]
    assert nxt["character"]["age_quarters"] == 1
    assert nxt["character"]["age_years"] == 0
    assert nxt["character"]["age_months"] == 3
    assert nxt["last_outcome"]
    year = nxt
    for _ in range(3):
        stepped = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
        assert stepped.status_code == 200, stepped.text
        year = stepped.json()["save"]
    assert year["character"]["age_quarters"] == 4
    assert year["character"]["age_years"] == 1
    assert year["character"]["age_months"] == 0
    assert len(nxt["history"]) == 1
    assert nxt["alive"] is True


async def test_incompatible_save_is_retired(client):
    headers, user_id = await open_session(client, "session-old-00001")
    await server.db.saves.insert_one(
        {
            "user_id": user_id,
            "needs": {"hunger": 1},
            "character": {"name": "Old"},
            "deleted_at": None,
        }
    )
    state = await client.get("/api/game/state", headers=headers)
    assert state.status_code == 200
    assert state.json()["save"] is None
    retired = await server.db.saves.find_one({"user_id": user_id})
    assert retired["deleted_at"] is not None


async def test_migrate_repairs_a_thin_save(client):
    headers, user_id = await open_session(client, "session-thin-0001")
    await server.db.saves.insert_one(
        {
            "user_id": user_id,
            "generation": 1,
            "alive": True,
            "character": {
                "name": "Bea",
                "background": "A steady house",
                "background_key": "stable",
                "age_years": 3,
                "stats": {
                    "health": 10,
                    "happiness": 10,
                    "smarts": 10,
                    "looks": 10,
                    "money": 10,
                    "reputation": 10,
                    "family": 10,
                },
                "flags": {key: 10 for key in server.FLAG_KEYS},
            },
            "deleted_at": None,
        }
    )
    state = await client.get("/api/game/state", headers=headers)
    character = state.json()["save"]["character"]
    assert character["partner"] is None
    assert character["business"] is None
    assert character["species"] == "human"
    assert character["stage"] == "child"
    assert state.json()["save"]["current_event"]["title"]


async def test_death_grants_marks_and_heir_inherits(client):
    headers, user_id = await open_session(client, "session-heir-0001")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "poverty"},
    )
    assert created.status_code == 200
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["character"].pop("age_quarters", None)
    stored["character"].pop("age_months", None)
    stored["character"].pop("age_unit", None)
    stored["character"]["age_years"] = 80
    stored["character"]["stats"]["money"] = 1000
    stored["character"]["stats"]["reputation"] = 40
    stored["character"]["children"] = [{"id": "child-1", "name": "Mina", "born_parent_age": 30}]
    stored["current_event"] = {
        "title": "The end",
        "narrative": "It is time.",
        "choices": [
            {"label": "Let go", "outcome": "The light goes ordinary.", "effects": {}, "flags": {}, "fatal": True},
            {"label": "Hold", "outcome": "Not yet.", "effects": {}, "flags": {}},
        ],
    }
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": stored["character"], "current_event": stored["current_event"]}},
    )
    died = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert died.status_code == 200, died.text
    body = died.json()
    assert body["save"]["alive"] is False
    assert body["marks_earned"] == 50 + 20 + 40 + 10
    assert body["profile"]["marks"] == 250 + body["marks_earned"]
    assert body["profile"]["lives_lived"] == 1
    heirs = await client.get("/api/game/heirs", headers=headers)
    assert heirs.status_code == 200
    listed = heirs.json()["heirs"]
    assert listed[0]["id"] == "child-1"
    assert listed[0]["age_now"] == 50
    assert listed[-1]["id"] == "new"
    assert "You earned" not in heirs.json()["obituary"]
    assert "Ada" in heirs.json()["obituary"]
    continued = await client.post("/api/game/heir", headers=headers, json={"heir_id": "child-1"})
    assert continued.status_code == 200, continued.text
    nxt = continued.json()["save"]
    assert nxt["alive"] is True
    assert nxt["generation"] == 2
    assert nxt["character"]["name"] == "Mina"
    assert nxt["character"]["age_years"] == 50
    assert nxt["character"]["stats"]["money"] == 500
    assert nxt["lineage"][0]["heir_name"] == "Mina"
    assert nxt["lineage"][0]["name"] == "Ada"


async def test_distant_relative_and_abandon_keeps_marks(client):
    headers, user_id = await open_session(client, "session-far-00001")
    await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["current_event"] = {
        "title": "The end",
        "narrative": "It is time.",
        "choices": [
            {"label": "Let go", "outcome": "Done.", "effects": {}, "flags": {}, "fatal": True},
            {"label": "Hold", "outcome": "No.", "effects": {}, "flags": {}},
        ],
    }
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"current_event": stored["current_event"]}},
    )
    await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    continued = await client.post(
        "/api/game/heir",
        headers=headers,
        json={"heir_id": "new", "name": "Rowan Hale"},
    )
    assert continued.status_code == 200
    assert continued.json()["save"]["character"]["name"] == "Rowan Hale"
    assert continued.json()["save"]["character"]["age_years"] == 0
    abandoned = await client.post("/api/game/abandon", headers=headers)
    assert abandoned.status_code == 200
    state = await client.get("/api/game/state", headers=headers)
    assert state.json()["save"] is None
    profile = await client.get("/api/profile", headers=headers)
    assert profile.json()["profile"]["lives_lived"] == 1
    assert profile.json()["profile"]["marks"] > 250


async def test_store_buy_grants_and_rejects_duplicates(client):
    headers, _user_id = await open_session(client, "session-shop-0001")
    await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    catalog = await client.get("/api/store", headers=headers)
    assert catalog.status_code == 200
    ids = {pack["id"] for pack in catalog.json()["packs"]}
    assert "supernatural-vampire" in ids
    assert catalog.json()["marks"] == 250
    assert catalog.json()["coins"] == 0
    vampire = next(pack for pack in catalog.json()["packs"] if pack["id"] == "supernatural-vampire")
    assert vampire["currency"] == "coins"
    assert vampire["cost"] == 2500
    coat_pack = next(pack for pack in catalog.json()["packs"] if pack["id"] == "cosmetic-coat")
    assert coat_pack["currency"] == "marks"
    assert coat_pack["cost"] == 50
    coat = await client.post("/api/store/buy", headers=headers, json={"pack_id": "cosmetic-coat"})
    assert coat.status_code == 200, coat.text
    assert coat.json()["profile"]["marks"] == 200
    assert "Black Wool Coat" in coat.json()["profile"]["unlocks"]["cosmetics"]
    charm = await client.post("/api/store/buy", headers=headers, json={"pack_id": "skill-charm"})
    assert charm.status_code == 200, charm.text
    assert charm.json()["profile"]["marks"] == 100
    state = await client.get("/api/game/state", headers=headers)
    assert state.json()["save"]["character"]["flags"]["charisma"] == 53
    duplicate = await client.post("/api/store/buy", headers=headers, json={"pack_id": "skill-charm"})
    assert duplicate.status_code == 409
    thirsty = await client.post("/api/store/buy", headers=headers, json={"pack_id": "supernatural-vampire"})
    assert thirsty.status_code == 402
    assert thirsty.json()["detail"] == "Not enough Coins"
    after = await client.get("/api/profile", headers=headers)
    assert after.json()["profile"]["marks"] == 100
    assert after.json()["profile"]["coins"] == 0
    missing = await client.post("/api/store/buy", headers=headers, json={"pack_id": "not-real"})
    assert missing.status_code == 404


async def test_year_save_migrates_to_quarters_once(client):
    headers, user_id = await open_session(client, "session-migrate-q")
    await server.db.saves.insert_one(
        {
            "user_id": user_id,
            "generation": 1,
            "alive": True,
            "character": {
                "name": "Bea",
                "background": "A steady house",
                "background_key": "stable",
                "age_years": 24,
                "partner_seen_age": 20,
                "partner": {"name": "June", "status": "dating", "bond": 40},
                "children": [{"id": "c1", "name": "Mina", "born_parent_age": 18}],
                "species": "vampire",
                "species_data": {"clan": "Ash Court", "bloodlust": 20, "masquerade": 70, "last_power_age": 10},
                "stats": {"health": 70, "happiness": 60, "smarts": 50, "looks": 50, "money": 400, "reputation": 40, "family": 50},
                "flags": {key: 40 for key in server.FLAG_KEYS},
            },
            "deleted_at": None,
        }
    )
    state = await client.get("/api/game/state", headers=headers)
    character = state.json()["save"]["character"]
    assert character["age_quarters"] == 96
    assert character["age_years"] == 24
    assert character["age_unit"] == "quarters"
    assert character["partner_seen_age"] == 80
    assert character["children"][0]["born_parent_age"] == 72
    assert character["species_data"]["last_power_age"] == 40
    again = await client.get("/api/game/state", headers=headers)
    assert again.json()["save"]["character"]["age_quarters"] == 96
