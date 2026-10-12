import server
from server import (
    AGE_END_CAUSE,
    HUNTER_DEATH_CAUSE,
    IMMORTAL_PRODUCT_ID,
    LAST_AGE,
    TEST_PURCHASE_RECEIPT,
    advance_quarter,
    fresh_character,
    set_age,
)


async def open_session(client, session_id: str, name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


async def _buy(client, headers, pack_id: str):
    return await client.post("/api/store/buy", headers=headers, json={"pack_id": pack_id})


async def _verify(client, headers, product_id: str, receipt: str = TEST_PURCHASE_RECEIPT, active: bool | None = None):
    payload: dict = {"product_id": product_id, "receipt": receipt}
    if active is not None:
        payload["active"] = active
    return await client.post("/api/store/purchase/verify", headers=headers, json=payload)


async def test_new_profile_starts_with_marks_and_zero_coins(client):
    headers, _user_id = await open_session(client, "session-coins-new")
    profile = await client.get("/api/profile", headers=headers)
    body = profile.json()["profile"]
    assert body["marks"] == 250
    assert body["coins"] == 0
    assert body["immortal"] is False


async def test_profile_migration_sets_coins_to_zero(client):
    headers, user_id = await open_session(client, "session-coins-migrate")
    for doc in server.db.profiles.docs:
        if doc.get("user_id") == user_id:
            doc.pop("coins", None)
            doc.pop("entitlements", None)
    profile = await client.get("/api/profile", headers=headers)
    body = profile.json()["profile"]
    assert body["marks"] == 250
    assert body["coins"] == 0
    assert body["immortal"] is False


async def test_marks_and_coins_purchases_deduct_the_right_balance(client):
    headers, _user_id = await open_session(client, "session-coins-buy")
    marks = await _buy(client, headers, "cosmetic-coat")
    assert marks.status_code == 200, marks.text
    assert marks.json()["profile"]["marks"] == 200
    assert marks.json()["profile"]["coins"] == 0
    broke = await _buy(client, headers, "lifestyle-lease")
    assert broke.status_code == 200, broke.text
    short = await _buy(client, headers, "career-medicine")
    assert short.status_code == 402
    assert short.json()["detail"] == "Not enough Legacy Marks"
    untouched = await client.get("/api/profile", headers=headers)
    assert untouched.json()["profile"]["marks"] == 50
    assert "career-medicine" not in untouched.json()["profile"]["owned_packs"]
    thirsty = await _buy(client, headers, "supernatural-vampire")
    assert thirsty.status_code == 402
    assert thirsty.json()["detail"] == "Not enough Coins"
    still = await client.get("/api/profile", headers=headers)
    assert still.json()["profile"]["marks"] == 50
    assert still.json()["profile"]["coins"] == 0
    granted = await _verify(client, headers, "com.anvilandember.legacy.coins2500")
    assert granted.status_code == 200, granted.text
    assert granted.json()["coins_granted"] == 2500
    assert granted.json()["profile"]["coins"] == 2500
    assert granted.json()["profile"]["marks"] == 50
    bought = await _buy(client, headers, "supernatural-vampire")
    assert bought.status_code == 200, bought.text
    assert bought.json()["profile"]["coins"] == 0
    assert bought.json()["profile"]["marks"] == 50
    assert "vampire" in bought.json()["profile"]["unlocks"]["species"]


async def test_unverified_receipt_grants_nothing(client):
    headers, _user_id = await open_session(client, "session-coins-stub")
    refused = await _verify(client, headers, "com.anvilandember.legacy.coins100", receipt="client-says-trust-me")
    assert refused.status_code == 400
    profile = await client.get("/api/profile", headers=headers)
    assert profile.json()["profile"]["coins"] == 0
    minted = await client.post("/api/store/buy", headers=headers, json={"pack_id": "coins100"})
    assert minted.status_code == 404


async def test_immortal_survives_old_age_and_lapse_dies_on_schedule():
    immortal = fresh_character("Ada", "stable", [])
    set_age(immortal, 70 * 4)
    immortal["stats"]["health"] = 70
    for _ in range(400):
        assert advance_quarter(immortal, [], True) is None
    assert immortal["age_quarters"] == 70 * 4 + 400
    assert immortal["age_years"] == 170
    assert immortal["stats"]["health"] == 70

    lapsed = fresh_character("Bea", "stable", [])
    set_age(lapsed, LAST_AGE - 1)
    lapsed["stats"]["health"] = 80
    assert advance_quarter(lapsed, [], True) is None
    assert lapsed["age_quarters"] == LAST_AGE
    assert advance_quarter(lapsed, [], False) == AGE_END_CAUSE

    resumed = fresh_character("Cal", "stable", [])
    set_age(resumed, 80 * 4 - 1)
    resumed["stats"]["health"] = 70
    assert advance_quarter(resumed, [], False) is None
    assert resumed["stats"]["health"] == 69
    assert resumed["age_years"] == 80


async def test_immortal_still_dies_to_hunter_heat():
    character = fresh_character("Ada", "stable", [], species="vampire")
    set_age(character, 40 * 4)
    character["hunter_heat"] = 100
    cause = advance_quarter(character, [], True)
    assert cause == HUNTER_DEATH_CAUSE
    assert character["age_years"] > 100 or character["stats"]["health"] > 0


async def test_api_immortal_survives_the_cap_and_hunter_still_ends_it(client):
    headers, user_id = await open_session(client, "session-immortal-age")
    created = await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    assert created.status_code == 200, created.text
    turned = await _verify(client, headers, IMMORTAL_PRODUCT_ID, active=True)
    assert turned.status_code == 200, turned.text
    assert turned.json()["immortal"] is True
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["character"]["age_quarters"] = LAST_AGE - 1
    stored["character"]["stats"]["health"] = 80
    stored["current_event"] = {
        "title": "A quiet season",
        "narrative": "Nothing asks to be finished.",
        "choices": [{"label": "Stay", "outcome": "You do.", "effects": {}, "flags": {}}],
    }
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": stored["character"], "current_event": stored["current_event"]}},
    )
    lived = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert lived.status_code == 200, lived.text
    assert lived.json()["save"]["alive"] is True
    assert lived.json()["save"]["character"]["age_quarters"] == LAST_AGE
    off = await _verify(client, headers, IMMORTAL_PRODUCT_ID, active=False)
    assert off.json()["immortal"] is False
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["current_event"] = {
        "title": "Another season",
        "narrative": "The calendar is back.",
        "choices": [{"label": "Stay", "outcome": "You do.", "effects": {}, "flags": {}}],
    }
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"current_event": stored["current_event"]}},
    )
    ended = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert ended.status_code == 200, ended.text
    assert ended.json()["save"]["alive"] is False
    assert ended.json()["save"]["true_death"] is False
    assert ended.json()["save"]["cause_of_death"] == AGE_END_CAUSE

    headers, user_id = await open_session(client, "session-immortal-hunt")
    await client.post("/api/game/new", headers=headers, json={"name": "Eve", "background_key": "stable"})
    await _verify(client, headers, IMMORTAL_PRODUCT_ID, active=True)
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["character"]["species"] = "vampire"
    stored["character"]["species_data"] = {"clan": "Ash Court", "bloodlust": 20, "masquerade": 70, "last_power_age": None}
    stored["character"]["hunter_heat"] = 100
    stored["current_event"] = {
        "title": "A quiet season",
        "narrative": "Hunters are already in the street.",
        "choices": [{"label": "Stay", "outcome": "You do.", "effects": {}, "flags": {}}],
    }
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": stored["character"], "current_event": stored["current_event"]}},
    )
    hunted = await client.post("/api/game/choice", headers=headers, json={"choice_index": 0})
    assert hunted.status_code == 200, hunted.text
    assert hunted.json()["save"]["alive"] is False
    assert hunted.json()["save"]["true_death"] is True
    assert "Hunters" in hunted.json()["save"]["cause_of_death"]


def _line():
    return {
        "children": [
            {
                "id": "child-mina",
                "name": "Mina",
                "born_parent_age": 80,
                "children": [
                    {
                        "id": "grand-eli",
                        "name": "Eli",
                        "born_parent_age": 80,
                        "children": [
                            {
                                "id": "great-ruth",
                                "name": "Ruth",
                                "born_parent_age": 40,
                                "children": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }


async def test_descendants_span_three_generations_and_torch_reaches_a_grandchild(client):
    headers, user_id = await open_session(client, "session-torch")
    await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "wealthy"})
    await _verify(client, headers, IMMORTAL_PRODUCT_ID, active=True)
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    stored["character"]["age_quarters"] = 80 * 4
    stored["character"]["age_years"] = 80
    stored["character"]["stats"]["money"] = 1000
    stored["character"]["children"] = _line()["children"]
    await server.db.saves.update_one(
        {"user_id": user_id, "deleted_at": None},
        {"$set": {"character": stored["character"]}},
    )
    listed = await client.get("/api/game/descendants", headers=headers)
    assert listed.status_code == 200, listed.text
    by_depth = {item["generation_depth"]: item for item in listed.json()["descendants"]}
    assert set(by_depth) >= {1, 2, 3}
    assert by_depth[1]["relation"] == "child"
    assert by_depth[1]["name"] == "Mina"
    assert by_depth[2]["relation"] == "grandchild"
    assert by_depth[2]["name"] == "Eli"
    assert by_depth[3]["relation"] == "great-grandchild"
    assert by_depth[3]["name"] == "Ruth"
    before = await client.get("/api/profile", headers=headers)
    passed = await client.post("/api/game/pass-torch", headers=headers, json={"descendant_id": "grand-eli"})
    assert passed.status_code == 200, passed.text
    save = passed.json()["save"]
    assert save["alive"] is True
    assert save["generation"] == 2
    assert save["true_death"] is False
    assert save["cause_of_death"] is None
    assert save["character"]["name"] == "Eli"
    assert save["character"]["age_years"] == 40
    assert save["character"]["stats"]["money"] == 500
    assert "died" not in save["character"]["life_log"][0]
    assert "passed the life" in save["character"]["life_log"][0]
    record = save["lineage"][-1]
    assert record["torch_passed"] is True
    assert record["cause_of_death"] is None
    assert record["heir_name"] == "Eli"
    assert "died" not in record["epitaph"]
    after = await client.get("/api/profile", headers=headers)
    assert after.json()["profile"]["marks"] == before.json()["profile"]["marks"]
    assert after.json()["profile"]["lives_lived"] == before.json()["profile"]["lives_lived"]


async def test_torch_rejected_without_immortality_or_descendants(client):
    headers, user_id = await open_session(client, "session-torch-no")
    await client.post("/api/game/new", headers=headers, json={"name": "Ada", "background_key": "stable"})
    denied = await client.post("/api/game/pass-torch", headers=headers, json={"descendant_id": "nobody"})
    assert denied.status_code == 403
    await _verify(client, headers, IMMORTAL_PRODUCT_ID, active=True)
    empty = await client.post("/api/game/pass-torch", headers=headers, json={"descendant_id": "nobody"})
    assert empty.status_code == 409
    assert "descendant" in empty.json()["detail"].lower()
    stored = await server.db.saves.find_one({"user_id": user_id, "deleted_at": None})
    assert stored["alive"] is True
    assert stored["character"]["name"] == "Ada"
