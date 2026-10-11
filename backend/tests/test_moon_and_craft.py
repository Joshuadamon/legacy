import server

from server import LYCAN_SUBTYPES


async def open_session(client, session_id: str, name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def grant(user_id: str, pack_id: str) -> None:
    await server.db.profiles.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$addToSet": {"owned_packs": pack_id}},
    )


async def rewrite_character(user_id: str, **fields) -> dict:
    save = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = save["character"]
    character.update(fields)
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character}},
    )
    return character


async def test_lycan_birth_requires_the_pack_and_keeps_a_subtype(client):
    headers, user_id = await open_session(client, "session-lycan-birth")
    denied = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable", "species": "lycanthrope", "subtype": "wolf"},
    )
    assert denied.status_code == 200, denied.text
    assert denied.json()["save"]["character"]["species"] == "human"
    await client.post("/api/game/abandon", headers=headers)

    await grant(user_id, "supernatural-lycanthrope")
    unknown = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable", "species": "dragon"},
    )
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["save"]["character"]["species"] == "human"
    await client.post("/api/game/abandon", headers=headers)

    born = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable", "species": "lycanthrope", "subtype": "wolf"},
    )
    assert born.status_code == 200, born.text
    save = born.json()["save"]
    data = save["character"]["species_data"]
    assert "_id" not in save
    assert save["character"]["species"] == "lycanthrope"
    assert data["subtype"] == "wolf"
    assert data["moon"] == 20
    assert data["control"] == 64
    assert isinstance(data["pack"]["name"], str) and data["pack"]["name"]
    assert len(data["pack"]["members"]) == 3
    await client.post("/api/game/abandon", headers=headers)

    rolled = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Bea", "background_key": "stable", "species": "lycanthrope"},
    )
    assert rolled.status_code == 200, rolled.text
    assert rolled.json()["save"]["character"]["species_data"]["subtype"] in LYCAN_SUBTYPES


async def test_witch_birth_requires_the_pack(client):
    headers, user_id = await open_session(client, "session-witch-birth")
    denied = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Cara", "background_key": "stable", "species": "witch"},
    )
    assert denied.status_code == 200, denied.text
    assert denied.json()["save"]["character"]["species"] == "human"
    await client.post("/api/game/abandon", headers=headers)

    await grant(user_id, "supernatural-witch")
    born = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Cara", "background_key": "stable", "species": "witch"},
    )
    assert born.status_code == 200, born.text
    save = born.json()["save"]
    data = save["character"]["species_data"]
    assert "_id" not in save
    assert save["character"]["species"] == "witch"
    assert data["mana"] == 48
    assert data["notoriety"] == 12
    assert isinstance(data["coven"]["name"], str) and data["coven"]["name"]
    assert len(data["coven"]["members"]) == 3


async def test_bite_and_awakening_wait_for_the_pack_and_thirteen(client):
    headers, user_id = await open_session(client, "session-turn-both")
    created = await client.post("/api/game/new", headers=headers, json={"name": "Dee", "background_key": "stable"})
    assert created.status_code == 200, created.text
    await rewrite_character(user_id, age_years=20)
    no_moon = await client.post("/api/game/transform", headers=headers, json={"species": "lycanthrope"})
    assert no_moon.status_code == 403
    assert "not yours" in no_moon.json()["detail"]
    no_craft = await client.post("/api/game/transform", headers=headers, json={"species": "witch"})
    assert no_craft.status_code == 403
    assert "not yours" in no_craft.json()["detail"]

    await grant(user_id, "supernatural-lycanthrope")
    await grant(user_id, "supernatural-witch")
    await rewrite_character(user_id, age_years=12)
    young = await client.post("/api/game/transform", headers=headers, json={"species": "lycanthrope", "subtype": "stag"})
    assert young.status_code == 403
    assert "thirteen" in young.json()["detail"]

    await rewrite_character(user_id, age_years=13)
    bitten = await client.post("/api/game/transform", headers=headers, json={"species": "lycanthrope", "subtype": "stag"})
    assert bitten.status_code == 200, bitten.text
    bitten_body = bitten.json()["save"]
    assert "_id" not in bitten_body
    assert bitten_body["character"]["species"] == "lycanthrope"
    assert bitten_body["character"]["species_data"]["subtype"] == "stag"
    assert bitten_body["character"]["species_data"]["pack"]["members"]

    again = await client.post("/api/game/transform", headers=headers, json={"species": "witch"})
    assert again.status_code == 409
    assert "already" in again.json()["detail"]

    await client.post("/api/game/abandon", headers=headers)
    human = await client.post("/api/game/new", headers=headers, json={"name": "Eve", "background_key": "stable"})
    assert human.status_code == 200, human.text
    await rewrite_character(user_id, age_years=16)
    woke = await client.post("/api/game/transform", headers=headers, json={"species": "witch"})
    assert woke.status_code == 200, woke.text
    woke_body = woke.json()["save"]
    assert woke_body["character"]["species"] == "witch"
    assert woke_body["character"]["species_data"]["coven"]["name"]
    assert "_id" not in woke_body


async def test_a_vampire_cannot_transform_again(client):
    headers, user_id = await open_session(client, "session-vamp-locked")
    await grant(user_id, "supernatural-vampire")
    await grant(user_id, "supernatural-lycanthrope")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Fay", "background_key": "stable", "species": "vampire"},
    )
    assert created.status_code == 200, created.text
    await rewrite_character(user_id, age_years=20)
    refused = await client.post("/api/game/transform", headers=headers, json={"species": "lycanthrope", "subtype": "wolf"})
    assert refused.status_code == 409
    assert "already" in refused.json()["detail"]
    assert created.json()["save"]["character"]["species"] == "vampire"


async def test_lycan_powers_are_once_a_year(client):
    headers, user_id = await open_session(client, "session-lycan-powers")
    await grant(user_id, "supernatural-lycanthrope")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Gil", "background_key": "stable", "species": "lycanthrope", "subtype": "bear"},
    )
    assert created.status_code == 200, created.text
    before = created.json()["save"]["character"]
    unknown = await client.post("/api/game/supernatural", headers=headers, json={"action": "ritual"})
    assert unknown.status_code == 400

    isolated = await client.post("/api/game/supernatural", headers=headers, json={"action": "isolate"})
    assert isolated.status_code == 200, isolated.text
    after = isolated.json()["save"]["character"]
    assert after["species_data"]["control"] == before["species_data"]["control"] + 18
    assert after["stats"]["happiness"] < before["stats"]["happiness"]
    assert after["species_data"]["last_power_age"] == 0

    spent = await client.post("/api/game/supernatural", headers=headers, json={"action": "hunt"})
    assert spent.status_code == 409

    aged = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert aged.status_code == 200, aged.text
    hunted = await client.post("/api/game/supernatural", headers=headers, json={"action": "hunt"})
    assert hunted.status_code == 200, hunted.text
    assert hunted.json()["save"]["character"]["hunter_heat"] > aged.json()["save"]["character"]["hunter_heat"]

    ran = await client.post("/api/game/supernatural", headers=headers, json={"action": "run_pack"})
    assert ran.status_code == 409


async def test_witch_ritual_spends_mana_once_a_year(client):
    headers, user_id = await open_session(client, "session-witch-powers")
    await grant(user_id, "supernatural-witch")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Hale", "background_key": "stable", "species": "witch"},
    )
    assert created.status_code == 200, created.text
    save = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = save["character"]
    character["species_data"]["mana"] = 10
    await server.db.saves.update_one({"user_id": user_id, "deleted_at": None}, {"$set": {"character": character}})

    dry = await client.post("/api/game/supernatural", headers=headers, json={"action": "ritual"})
    assert dry.status_code == 409
    assert "mana" in dry.json()["detail"]
    quiet = await client.post("/api/game/supernatural", headers=headers, json={"action": "lay_low"})
    assert quiet.status_code == 200, quiet.text
    assert quiet.json()["save"]["character"]["species_data"]["notoriety"] < 12
    assert quiet.json()["save"]["character"]["species_data"]["last_power_age"] == 0

    await client.post("/api/game/abandon", headers=headers)
    again = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ivo", "background_key": "stable", "species": "witch"},
    )
    assert again.status_code == 200, again.text
    cast = await client.post("/api/game/supernatural", headers=headers, json={"action": "ritual"})
    assert cast.status_code == 200, cast.text
    body = cast.json()["save"]["character"]
    assert body["species_data"]["mana"] == 20
    assert body["species_data"]["notoriety"] == 26
    assert body["hunter_heat"] == 8
    aged = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert aged.status_code == 200, aged.text
    hexed = await client.post("/api/game/supernatural", headers=headers, json={"action": "hex_rival"})
    assert hexed.status_code == 200, hexed.text
    assert hexed.json()["save"]["character"]["species_data"]["notoriety"] > aged.json()["save"]["character"]["species_data"]["notoriety"]


async def test_uncontrolled_shift_raises_hunter_heat(client):
    headers, user_id = await open_session(client, "session-lycan-shift")
    await grant(user_id, "supernatural-lycanthrope")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Jules", "background_key": "stable", "species": "lycanthrope", "subtype": "raven"},
    )
    assert created.status_code == 200, created.text
    before = created.json()["save"]["character"]
    data = before["species_data"]
    data["control"] = 20
    await rewrite_character(user_id, age_years=4, species_data=data, hunter_heat=0)

    ended = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert ended.status_code == 200, ended.text
    after = ended.json()["save"]
    assert after["alive"] is True
    assert after["character"]["species_data"]["moon"] == 100
    assert after["character"]["hunter_heat"] == 16
    assert after["character"]["stats"]["reputation"] < before["stats"]["reputation"]
    assert after["character"]["stats"]["health"] < before["stats"]["health"]
    assert "_id" not in after


async def test_high_notoriety_year_raises_hunter_heat(client):
    headers, user_id = await open_session(client, "session-witch-heat")
    await grant(user_id, "supernatural-witch")
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Kit", "background_key": "stable", "species": "witch"},
    )
    assert created.status_code == 200, created.text
    data = created.json()["save"]["character"]["species_data"]
    data["notoriety"] = 80
    data["mana"] = 30
    await rewrite_character(user_id, species_data=data, hunter_heat=4)

    year = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert year.status_code == 200, year.text
    body = year.json()["save"]
    assert body["alive"] is True
    assert body["character"]["hunter_heat"] == 12
    assert body["character"]["species_data"]["mana"] == 42
    assert "_id" not in body
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    assert stored["deleted_at"] is None
