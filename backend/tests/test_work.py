import server
from server import (
    BUSINESS_GROWTH_DIVISOR,
    BUSINESS_START_VALUE,
    FIELD_BASE,
    _migrate_character,
    _sanitize_event,
    advance_quarter,
    set_age,
    apply_choice,
    fresh_character,
)


def test_migrate_career_and_business_default_to_null():
    character = _migrate_character({"name": "Old", "age_years": 4, "stats": {}, "flags": {}})
    assert character["career"] is None
    assert character["business"] is None
    kept = _migrate_character(
        {
            "name": "Ada",
            "age_years": 40,
            "stats": {},
            "flags": {},
            "career": {"title": "Night clerk", "field": "labor", "level": 2, "income": 900},
            "business": {"name": "Hale's", "type": "shop", "value": 2500},
        }
    )
    assert kept["career"]["income"] == 900
    assert kept["career"]["level"] == 2
    assert kept["business"]["value"] == 2500


def test_level_up_raises_income_and_quitting_stops_it():
    character = fresh_character("Ada", "stable", [])
    set_age(character, 22 * 4)
    apply_choice(
        character,
        {"effects": {}, "flags": {}, "career_start": {"title": "Night clerk", "field": "labor"}},
    )
    assert character["career"]["income"] == FIELD_BASE["labor"]
    apply_choice(character, {"effects": {}, "flags": {}, "career_level": "up"})
    assert character["career"]["level"] == 2
    assert character["career"]["income"] == FIELD_BASE["labor"] * 2
    money = character["stats"]["money"]
    apply_choice(character, {"effects": {}, "flags": {}, "career_leave": True})
    assert character["career"] is None
    advance_quarter(character, [])
    assert character["stats"]["money"] == money


def test_business_compounds_over_years():
    character = fresh_character("Ada", "stable", [])
    set_age(character, 30 * 4)
    character["business"] = {"name": "Hale's", "type": "shop", "value": 1000}
    for _ in range(4):
        advance_quarter(character, [])
    assert 1000 < character["business"]["value"] <= 1000 + 1000 // BUSINESS_GROWTH_DIVISOR + 4
    grown = character["business"]["value"]
    for _ in range(4):
        advance_quarter(character, [])
    assert grown < character["business"]["value"] <= grown + max(1, grown // BUSINESS_GROWTH_DIVISOR) + 4


def test_sanitize_drops_a_locked_field_and_keeps_a_free_one():
    character = fresh_character("Ada", "stable", [])
    set_age(character, 24 * 4)
    event = _sanitize_event(
        {
            "title": "Work",
            "narrative": "A door.",
            "choices": [
                {"label": "Medicine", "outcome": "No.", "career_start": {"title": "Nurse", "field": "medicine"}},
                {"label": "Labor", "outcome": "Yes.", "career_start": {"title": "Clerk", "field": "labor"}, "business_event": 5000},
            ],
        },
        character,
    )
    assert event is not None
    assert "career_start" not in event["choices"][0]
    assert event["choices"][1]["career_start"]["field"] == "labor"
    assert event["choices"][1]["business_event"] == 5000


async def test_career_start_requires_the_pack_and_heir_keeps_the_shop(client):
    headers, user_id = await open_session(client)
    created = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert created.status_code == 200
    await _replace_event(
        user_id,
        {
            "title": "A ward",
            "narrative": "They might hire you.",
            "choices": [
                {
                    "label": "Apply",
                    "outcome": "You ask.",
                    "effects": {},
                    "flags": {},
                    "career_start": {"title": "Orderly", "field": "medicine"},
                },
                {"label": "Walk away", "outcome": "You do.", "effects": {}, "flags": {}},
            ],
        },
        age=22,
    )
    locked = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert locked.status_code == 403
    assert "not open" in locked.json()["detail"]
    state = await client.get("/api/game/state", headers=headers)
    assert state.json()["save"]["character"]["career"] is None
    assert state.json()["save"]["character"]["age_years"] == 22

    bought = await client.post("/api/store/buy", headers=headers, json={"pack_id": "career-medicine"})
    assert bought.status_code == 200, bought.text
    hired = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert hired.status_code == 200, hired.text
    career = hired.json()["save"]["character"]["career"]
    assert career["field"] == "medicine"
    assert career["level"] == 1
    assert career["income"] == FIELD_BASE["medicine"]
    assert hired.json()["save"]["character"]["stats"]["money"] > 100

    await _replace_event(
        user_id,
        {
            "title": "The step",
            "narrative": "A better number.",
            "choices": [
                {"label": "Take it", "outcome": "The stub agrees.", "effects": {}, "flags": {}, "career_level": "up"},
                {"label": "Stay", "outcome": "You stay.", "effects": {}, "flags": {}},
            ],
        },
    )
    promoted = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert promoted.json()["save"]["character"]["career"]["level"] == 2
    assert promoted.json()["save"]["character"]["career"]["income"] == FIELD_BASE["medicine"] * 2

    await _replace_event(
        user_id,
        {
            "title": "The box",
            "narrative": "It is not personal.",
            "choices": [
                {"label": "Take the box", "outcome": "The wage stops.", "effects": {}, "flags": {}, "career_leave": True},
                {"label": "Ask", "outcome": "They think.", "effects": {}, "flags": {}},
            ],
        },
    )
    before = promoted.json()["save"]["character"]["stats"]["money"]
    fired = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert fired.json()["save"]["character"]["career"] is None
    assert fired.json()["save"]["character"]["stats"]["money"] == before

    await _replace_event(
        user_id,
        {
            "title": "A door",
            "narrative": "A lease.",
            "choices": [
                {
                    "label": "Open it",
                    "outcome": "A sign.",
                    "effects": {},
                    "flags": {},
                    "business_start": {"name": "Hale's", "type": "shop"},
                },
                {"label": "Wait", "outcome": "Not yet.", "effects": {}, "flags": {}},
            ],
        },
    )
    opened = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    shop = opened.json()["save"]["character"]["business"]
    assert shop["name"] == "Hale's"
    assert BUSINESS_START_VALUE < shop["value"] < BUSINESS_START_VALUE + BUSINESS_START_VALUE // BUSINESS_GROWTH_DIVISOR

    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["character"].pop("age_quarters", None)
    stored["character"].pop("age_months", None)
    stored["character"].pop("age_unit", None)
    stored["character"]["age_years"] = 80
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
    assert died.json()["save"]["alive"] is False
    continued = await client.post("/api/game/heir", headers=headers, json={"heir_id": "child-1"})
    assert continued.status_code == 200, continued.text
    heir = continued.json()["save"]["character"]
    assert heir["career"] is None
    assert heir["business"]["name"] == "Hale's"
    assert heir["business"]["type"] == "shop"
    assert heir["business"]["value"] == shop["value"]


async def open_session(client, session_id: str = "session-work-0001", name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def _replace_event(user_id: str, event: dict, age: int | None = None) -> None:
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    update = {"current_event": event}
    if age is not None:
        stored["character"].pop("age_quarters", None)
        stored["character"].pop("age_months", None)
        stored["character"].pop("age_unit", None)
        stored["character"]["age_years"] = age
        stored["character"]["stage"] = "young_adult"
        update["character"] = stored["character"]
    await server.db.saves.update_one({"user_id": user_id, "deleted_at": None}, {"$set": update})
