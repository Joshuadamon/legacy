import server
from server import (
    BOND_BREAK_AT,
    BOND_MARRY,
    BOND_NEGLECT_DROP,
    BOND_START,
    _migrate_character,
    _sanitize_event,
    advance_life,
    apply_choice,
    epitaph,
    fallback_event,
    fresh_character,
)


def test_choice_sets_a_partner_and_marriage_requires_dating():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 28
    apply_choice(
        character,
        {"effects": {}, "flags": {}, "partner_set": {"name": "June", "status": "married"}},
    )
    assert character["partner"] is None
    apply_choice(
        character,
        {"effects": {}, "flags": {}, "partner_set": {"name": "June", "status": "dating"}},
    )
    assert character["partner"] == {"name": "June", "status": "dating", "bond": BOND_START}
    assert any("Met June" in line for line in character["life_log"])
    apply_choice(
        character,
        {"effects": {}, "flags": {}, "partner_set": {"name": "June", "status": "married"}},
    )
    assert character["partner"]["status"] == "married"
    assert character["partner"]["name"] == "June"
    assert character["partner"]["bond"] == BOND_START + BOND_MARRY
    assert 0 <= character["partner"]["bond"] <= 100


def test_partner_end_clears_the_record():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 30
    apply_choice(
        character,
        {"effects": {}, "flags": {}, "partner_set": {"name": "June", "status": "dating"}},
    )
    apply_choice(character, {"effects": {}, "flags": {}, "partner_end": True})
    assert character["partner"] is None
    assert any("left the record" in line for line in character["life_log"])


def test_neglect_lowers_bond_and_a_low_bond_offers_a_breakup():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 30
    character["partner"] = {"name": "June", "status": "dating", "bond": 50}
    character["partner_seen_age"] = 30
    advance_life(character, [])
    advance_life(character, [])
    assert character["partner"]["bond"] == 50
    advance_life(character, [])
    assert character["partner"]["bond"] == 50 - BOND_NEGLECT_DROP
    character["partner"]["bond"] = BOND_BREAK_AT
    event = fallback_event(character, [], 1)
    assert event["choices"][0]["partner_end"] is True
    assert "June" in event["narrative"]


def test_child_born_names_the_partner():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 30
    character["partner"] = {"name": "June", "status": "married", "bond": 70}
    apply_choice(
        character,
        {"effects": {}, "flags": {}, "child_born": True, "child_name": "Mina"},
    )
    assert character["children"][0]["name"] == "Mina"
    assert character["children"][0]["other_parent"] == "June"


def test_migrate_partner_defaults_to_null_and_clamps_bond():
    empty = _migrate_character({"name": "Old", "age_years": 4, "stats": {}, "flags": {}})
    assert empty["partner"] is None
    assert empty["partner_seen_age"] is None
    kept = _migrate_character(
        {
            "name": "Ada",
            "age_years": 40,
            "stats": {},
            "flags": {},
            "partner": {"name": "June", "status": "married", "bond": 140},
        }
    )
    assert kept["partner"] == {"name": "June", "status": "married", "bond": 100}


def test_sanitize_keeps_partner_fields():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 24
    event = _sanitize_event(
        {
            "title": "A year",
            "narrative": "Someone stays.",
            "choices": [
                {
                    "label": "Stay",
                    "outcome": "You do.",
                    "partner_set": {"name": "  June  ", "status": "dating"},
                },
                {"label": "Leave", "outcome": "You don't.", "partner_end": True, "partner_set": {"name": "No", "status": "soulmate"}},
            ],
        },
        character,
    )
    assert event is not None
    assert event["choices"][0]["partner_set"] == {"name": "June", "status": "dating"}
    assert event["choices"][1]["partner_end"] is True
    assert "partner_set" not in event["choices"][1]


def test_epitaph_records_name_and_status():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 80
    character["partner"] = {"name": "June", "status": "married", "bond": 40}
    save = {
        "generation": 1,
        "alive": False,
        "cause_of_death": "The body kept its own calendar.",
        "character": character,
    }
    record = epitaph(save, "child-1", "Mina")
    assert record["partner"] == {"name": "June", "status": "married"}
    assert "married" in record["epitaph"]
    assert "June" in record["epitaph"]


async def test_choice_arc_and_death_epitaph_name_the_partner(client):
    headers, user_id = await open_session(client)
    created = await client.post(
        "/api/game/new",
        headers=headers,
        json={"name": "Ada", "background_key": "stable"},
    )
    assert created.status_code == 200

    await _replace_event(
        user_id,
        {
            "title": "Breakfast",
            "narrative": "Someone stays.",
            "choices": [
                {
                    "label": "Ask them to stay",
                    "outcome": "A second key.",
                    "effects": {},
                    "flags": {},
                    "partner_set": {"name": "June", "status": "dating"},
                },
                {"label": "Let them go", "outcome": "The door closes.", "effects": {}, "flags": {}},
            ],
        },
        age=22,
    )
    dated = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert dated.status_code == 200, dated.text
    partner = dated.json()["save"]["character"]["partner"]
    assert partner["name"] == "June"
    assert partner["status"] == "dating"
    assert partner["bond"] == BOND_START

    await _replace_event(
        user_id,
        {
            "title": "A witness",
            "narrative": "June asks.",
            "choices": [
                {
                    "label": "Marry them",
                    "outcome": "The record gets a second name.",
                    "effects": {},
                    "flags": {},
                    "partner_set": {"name": "June", "status": "married"},
                },
                {"label": "Not yet", "outcome": "You wait.", "effects": {}, "flags": {}},
            ],
        },
    )
    married = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert married.json()["save"]["character"]["partner"]["status"] == "married"

    await _replace_event(
        user_id,
        {
            "title": "A child",
            "narrative": "June is there.",
            "choices": [
                {
                    "label": "Take the child in",
                    "outcome": "A name in the house.",
                    "effects": {},
                    "flags": {},
                    "child_born": True,
                    "child_name": "Mina",
                },
                {"label": "Not now", "outcome": "The question waits.", "effects": {}, "flags": {}},
            ],
        },
        age=30,
    )
    born = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    child = born.json()["save"]["character"]["children"][0]
    assert child["name"] == "Mina"
    assert child["other_parent"] == "June"

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
        age=80,
    )
    died = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert died.json()["save"]["alive"] is False
    heirs = await client.get("/api/game/heirs", headers=headers)
    assert "June" in heirs.json()["obituary"]
    assert "married" in heirs.json()["obituary"]
    continued = await client.post("/api/game/heir", headers=headers, json={"heir_id": born.json()["save"]["character"]["children"][0]["id"]})
    assert continued.status_code == 200, continued.text
    assert continued.json()["save"]["lineage"][0]["partner"] == {"name": "June", "status": "married"}


async def test_choice_can_end_a_partnership(client):
    headers, user_id = await open_session(client, "session-end-00001")
    await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    await _replace_event(
        user_id,
        {
            "title": "The door",
            "narrative": "June is packed.",
            "choices": [
                {"label": "Let them go", "outcome": "The key comes back.", "effects": {}, "flags": {}, "partner_end": True},
                {"label": "Ask them to stay", "outcome": "You talk.", "effects": {}, "flags": {}},
            ],
        },
    )
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["character"]["age_years"] = 34
    stored["character"]["partner"] = {"name": "June", "status": "dating", "bond": 40}
    stored["character"]["partner_seen_age"] = 34
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": stored["character"]}},
    )
    ended = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert ended.status_code == 200, ended.text
    assert ended.json()["save"]["character"]["partner"] is None


async def open_session(client, session_id: str = "session-partner-01", name: str = "Ada"):
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
