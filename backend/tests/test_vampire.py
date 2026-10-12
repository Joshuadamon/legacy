import server


async def open_session(client, session_id: str, name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def grant_thirst(user_id: str) -> None:
    await server.db.profiles.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$addToSet": {"owned_packs": "supernatural-vampire"}},
    )


async def rewrite_character(user_id: str, **fields) -> None:
    save = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = save["character"]
    if "age_years" in fields and "age_quarters" not in fields:
        years = int(fields["age_years"])
        fields["age_quarters"] = years * 4
        fields["age_months"] = 0
        fields["age_unit"] = "quarters"
    character.update(fields)
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character}},
    )


async def test_vampire_birth_requires_the_pack(client):
    headers, user_id = await open_session(client, "session-vamp-birth")
    denied = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable", "species": "vampire", "clan": "Red Ledger"},
    )
    assert denied.status_code == 200, denied.text
    assert denied.json()["save"]["character"]["species"] == "human"
    assert denied.json()["save"]["character"]["species_data"] is None
    await client.post("/api/game/abandon", headers=headers)

    await grant_thirst(user_id)
    other = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable", "species": "witch"},
    )
    assert other.status_code == 200, other.text
    assert other.json()["save"]["character"]["species"] == "human"
    await client.post("/api/game/abandon", headers=headers)

    born = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable", "species": "vampire", "clan": "Red Ledger"},
    )
    assert born.status_code == 200, born.text
    save = born.json()["save"]
    assert "_id" not in save
    assert save["true_death"] is False
    assert save["character"]["species"] == "vampire"
    assert save["character"]["species_data"]["clan"] == "Red Ledger"
    assert save["character"]["species_data"]["bloodlust"] == 20
    assert save["character"]["species_data"]["masquerade"] == 72
    assert save["character"]["hunter_heat"] == 0


async def test_transform_rejects_until_the_pack_and_thirteen(client):
    headers, user_id = await open_session(client, "session-vamp-turn")
    created = await client.post("/api/game/new", headers=headers, json={"name": "Bea", "background_key": "stable"})
    assert created.status_code == 200, created.text
    await rewrite_character(user_id, age_years=20)
    early = await client.post("/api/game/transform", headers=headers, json={})
    assert early.status_code == 403
    assert "not yours" in early.json()["detail"]

    await grant_thirst(user_id)
    await rewrite_character(user_id, age_years=12)
    young = await client.post("/api/game/transform", headers=headers, json={"clan": "Quiet Parish"})
    assert young.status_code == 403
    assert "thirteen" in young.json()["detail"]

    await rewrite_character(user_id, age_years=13)
    turned = await client.post("/api/game/transform", headers=headers, json={"clan": "Quiet Parish"})
    assert turned.status_code == 200, turned.text
    character = turned.json()["save"]["character"]
    assert character["species"] == "vampire"
    assert character["species_data"]["clan"] == "Quiet Parish"
    assert "_id" not in turned.json()["save"]

    again = await client.post("/api/game/transform", headers=headers, json={})
    assert again.status_code == 409
    assert "already" in again.json()["detail"]


async def test_supernatural_actions_are_once_a_year(client):
    headers, user_id = await open_session(client, "session-vamp-powers")
    await grant_thirst(user_id)
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Cara", "background_key": "stable", "species": "vampire"},
    )
    assert created.status_code == 200, created.text

    unknown = await client.post("/api/game/supernatural", headers=headers, json={"action": "fly"})
    assert unknown.status_code == 400

    fed = await client.post("/api/game/supernatural", headers=headers, json={"action": "feed"})
    assert fed.status_code == 200, fed.text
    after = fed.json()["save"]["character"]
    assert after["species_data"]["bloodlust"] == 0
    assert after["species_data"]["masquerade"] == 62
    assert after["hunter_heat"] == 8
    assert after["species_data"]["last_power_age"] == 0
    assert fed.json()["outcome"]

    spent = await client.post("/api/game/supernatural", headers=headers, json={"action": "lay_low"})
    assert spent.status_code == 409
    assert "year" in spent.json()["detail"]

    for _ in range(3):
        stepped = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
        assert stepped.status_code == 200, stepped.text
        assert stepped.json()["save"]["character"]["age_years"] == 0
        still = await client.post("/api/game/supernatural", headers=headers, json={"action": "lay_low"})
        assert still.status_code == 409

    aged = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert aged.status_code == 200, aged.text
    assert aged.json()["save"]["character"]["age_years"] == 1
    assert aged.json()["save"]["character"]["age_quarters"] == 4

    low = await client.post("/api/game/supernatural", headers=headers, json={"action": "lay_low"})
    assert low.status_code == 200, low.text
    laid = low.json()["save"]["character"]
    assert laid["species_data"]["last_power_age"] == 4
    assert laid["hunter_heat"] < aged.json()["save"]["character"]["hunter_heat"]

    clan = await client.post("/api/game/supernatural", headers=headers, json={"action": "seek_clan"})
    assert clan.status_code == 409


async def test_human_cannot_spend_a_power(client):
    headers, _user_id = await open_session(client, "session-vamp-human")
    created = await client.post("/api/game/new", headers=headers, json={"name": "Dee", "background_key": "stable"})
    assert created.status_code == 200, created.text
    refused = await client.post("/api/game/supernatural", headers=headers, json={"action": "feed"})
    assert refused.status_code == 409
    assert "blood" in refused.json()["detail"]


async def test_hunter_heat_can_end_the_life(client):
    headers, user_id = await open_session(client, "session-vamp-heat")
    await grant_thirst(user_id)
    created = await client.post("/api/game/new", headers=headers, json={"name": "Eve", "background_key": "stable"})
    assert created.status_code == 200, created.text
    await rewrite_character(user_id, age_years=20)
    turned = await client.post("/api/game/transform", headers=headers, json={"clan": "Thorn Road"})
    assert turned.status_code == 200, turned.text

    save = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = save["character"]
    character["species_data"]["bloodlust"] = 100
    character["hunter_heat"] = 90
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character}},
    )

    body = None
    for _ in range(4):
        ended = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
        assert ended.status_code == 200, ended.text
        body = ended.json()["save"]
        if not body["alive"]:
            break
    assert body["alive"] is False
    assert body["true_death"] is True
    assert "Hunters" in body["cause_of_death"]
    assert "_id" not in body
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    assert stored["deleted_at"] is None
