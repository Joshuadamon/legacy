import server
from server import _migrate_save, epitaph, fresh_character


def test_epitaph_records_species_age_cause_partner_and_heir():
    character = fresh_character("Ada", "stable", [], species="witch")
    if hasattr(server, "set_age"):
        server.set_age(character, 64 * server.QUARTERS_PER_YEAR)
    else:
        character["age_years"] = 64
    character["partner"] = {"name": "June", "status": "dating", "bond": 40}
    save = {
        "generation": 2,
        "alive": False,
        "cause_of_death": "The craft answered back.",
        "character": character,
    }
    record = epitaph(save, "new", "Rowan")
    assert record["name"] == "Ada"
    assert record["species"] == "witch"
    assert record["age_at_death"] == 64
    assert "64" in str(record["years"])
    assert record["cause_of_death"] == "The craft answered back."
    assert record["partner"] == {"name": "June", "status": "dating"}
    assert record["heir_id"] == "new"
    assert record["heir_name"] == "Rowan"


def test_old_lineage_gains_species_and_age_at_death():
    save = _migrate_save(
        {
            "generation": 2,
            "character": fresh_character("Mina", "stable", []),
            "lineage": [
                {
                    "generation": 1,
                    "name": "Ada",
                    "years": "0–77",
                    "cause_of_death": "The light goes ordinary.",
                    "partner": {"name": "June", "status": "married"},
                    "heir_id": "child-1",
                    "heir_name": "Mina",
                    "epitaph": "Ada died at 77.",
                }
            ],
        }
    )
    row = save["lineage"][0]
    assert row["name"] == "Ada"
    assert row["species"] == "human"
    assert row["age_at_death"] == 77
    assert row["cause_of_death"] == "The light goes ordinary."
    assert row["partner"] == {"name": "June", "status": "married"}
    assert row["heir_name"] == "Mina"
    assert row["heir_id"] == "child-1"


async def open_session(client, session_id: str = "session-line-0001", name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def _end_life(user_id: str, *, age: int, species: str, partner: dict | None, child: dict | None) -> None:
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    character = stored["character"]
    if hasattr(server, "set_age"):
        server.set_age(character, age * server.QUARTERS_PER_YEAR)
        if child is not None:
            child = dict(child)
            child["born_parent_age"] = int(child["born_parent_age"]) * server.QUARTERS_PER_YEAR
    else:
        character["age_years"] = age
    character["species"] = species
    if species == "witch":
        character["species_data"] = {"mana": 40, "notoriety": 10, "coven": None, "last_power_age": None}
    elif species == "vampire":
        character["species_data"] = {"clan": "Ash Court", "bloodlust": 20, "masquerade": 70, "last_power_age": None}
    character["partner"] = partner
    character["children"] = [child] if child else []
    event = {
        "title": "The end",
        "narrative": "It is time.",
        "choices": [
            {"label": "Let go", "outcome": "The light goes ordinary.", "effects": {}, "flags": {}, "fatal": True},
            {"label": "Hold", "outcome": "Not yet.", "effects": {}, "flags": {}},
        ],
    }
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": character, "current_event": event}},
    )


async def test_three_generations_keep_the_line_in_order(client):
    headers, user_id = await open_session(client)
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "poverty"},
    )
    assert created.status_code == 200, created.text

    await _end_life(
        user_id,
        age=80,
        species="human",
        partner={"name": "June", "status": "married", "bond": 70},
        child={"id": "child-mina", "name": "Mina", "born_parent_age": 30},
    )
    died = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert died.status_code == 200, died.text
    assert died.json()["save"]["alive"] is False
    continued = await client.post("/api/game/heir", headers=headers, json={"heir_id": "child-mina"})
    assert continued.status_code == 200, continued.text

    await _end_life(
        user_id,
        age=54,
        species="witch",
        partner={"name": "Ellis", "status": "dating", "bond": 40},
        child={"id": "child-leo", "name": "Leo", "born_parent_age": 28},
    )
    died = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert died.status_code == 200, died.text
    continued = await client.post("/api/game/heir", headers=headers, json={"heir_id": "child-leo"})
    assert continued.status_code == 200, continued.text

    state = await client.get("/api/game/state", headers=headers)
    save = state.json()["save"]
    assert save["generation"] == 3
    assert save["character"]["name"] == "Leo"
    ada, mina = save["lineage"]
    assert [row["name"] for row in save["lineage"]] == ["Ada", "Mina"]
    assert ada["species"] == "human"
    assert ada["age_at_death"] == 80
    assert ada["cause_of_death"] == "The light goes ordinary."
    assert ada["partner"] == {"name": "June", "status": "married"}
    assert ada["heir_name"] == "Mina"
    assert mina["species"] == "witch"
    assert mina["age_at_death"] == 54
    assert mina["partner"] == {"name": "Ellis", "status": "dating"}
    assert mina["heir_name"] == "Leo"
    assert mina["generation"] == 2
