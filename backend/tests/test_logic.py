from server import (
    LYCAN_SUBTYPES,
    _migrate_character,
    _sanitize_event,
    advance_quarter,
    set_age,
    apply_choice,
    apply_owned_grants,
    compute_paths,
    fresh_character,
    marks_for_life,
    save_is_incompatible,
)


def test_marks_formula():
    character = fresh_character("Ada", "stable", [])
    set_age(character, 70 * 4)
    character["stats"]["reputation"] = 50
    assert marks_for_life(character, 1) == 50 + 25 + 35 + 10


def test_migrate_backfills_new_fields():
    character = _migrate_character({"name": "Old", "age_years": 4, "stats": {}, "flags": {}})
    assert character["stage"] == "child"
    assert character["partner"] is None
    assert character["career"] is None
    assert character["business"] is None
    assert character["species"] == "human"
    assert character["species_data"] is None
    assert character["hunter_heat"] == 0
    assert character["applied_grants"] == []
    assert "health" in character["stats"]
    assert "morality" in character["flags"]


def test_incompatible_legacy_save():
    assert save_is_incompatible({"needs": {"hunger": 1}, "character": {"name": "Old"}})
    assert not save_is_incompatible({"character": {"name": "New", "flags": {"morality": 1}}})


def test_paths_follow_flags():
    character = fresh_character("Ada", "rural_faith", [])
    set_age(character, 16 * 4)
    character["stage"] = "teen"
    paths = compute_paths(character, [])
    assert "devout" in paths
    assert "gray_market" not in paths


def test_skill_grant_applies_once():
    character = fresh_character("Ada", "stable", ["skill-charm"])
    assert character["flags"]["charisma"] == 53
    apply_owned_grants(character, ["skill-charm"])
    assert character["flags"]["charisma"] == 53


def test_career_pack_opens_a_path():
    character = fresh_character("Ada", "stable", ["career-medicine"])
    set_age(character, 22 * 4)
    paths = compute_paths(character, ["career-medicine"])
    assert "career:medicine" in paths


def test_sanitize_clamps_and_drops_garbage():
    character = fresh_character("Ada", "stable", [])
    set_age(character, 30 * 4)
    event = _sanitize_event(
        {
            "title": "A year",
            "narrative": "Something happens.",
            "choices": [
                {
                    "label": "Take it",
                    "outcome": "You do.",
                    "effects": {"health": 999, "money": 10, "not_a_stat": 5},
                    "flags": {"honesty": -999, "nope": 1},
                    "child_born": True,
                    "child_name": "Mina",
                },
                {"label": "Leave", "outcome": "You don't.", "fatal": True},
            ],
        },
        character,
    )
    assert event is not None
    assert event["choices"][0]["effects"]["health"] == 40
    assert event["choices"][0]["effects"]["money"] == 10
    assert "not_a_stat" not in event["choices"][0]["effects"]
    assert event["choices"][0]["flags"]["honesty"] == -40
    assert event["choices"][0]["child_born"] is True
    assert event["choices"][1]["fatal"] is True


def test_migrate_fills_vampire_meters():
    character = _migrate_character(
        {
            "name": "Ada",
            "age_years": 20,
            "stats": {},
            "flags": {},
            "species": "vampire",
            "species_data": {"bloodlust": 140, "masquerade": -5},
            "hunter_heat": 150,
        }
    )
    assert character["hunter_heat"] == 100
    assert character["species_data"]["clan"] == "Ash Court"
    assert character["species_data"]["bloodlust"] == 100
    assert character["species_data"]["masquerade"] == 0
    assert character["species_data"]["last_power_age"] is None


def test_sanitize_keeps_species_effects():
    character = fresh_character("Ada", "stable", [])
    set_age(character, 30 * 4)
    event = _sanitize_event(
        {
            "title": "Hunger",
            "narrative": "The night is loud.",
            "choices": [
                {
                    "label": "Go out",
                    "outcome": "You do.",
                    "species_effects": {"bloodlust": 999, "hunter_heat": -4, "nope": 8},
                },
                {"label": "Stay", "outcome": "You don't."},
            ],
        },
        character,
    )
    assert event is not None
    assert event["choices"][0]["species_effects"] == {"bloodlust": 40, "hunter_heat": -4}
    assert "species_effects" not in event["choices"][1]


def test_bloodlust_overflow_raises_hunter_heat():
    character = fresh_character("Ada", "stable", [ "supernatural-vampire"], species="vampire")
    character["species_data"]["bloodlust"] = 100
    character["hunter_heat"] = 90
    assert advance_quarter(character, ["supernatural-vampire"]) is None
    assert character["hunter_heat"] == 93
    for _ in range(2):
        assert advance_quarter(character, ["supernatural-vampire"]) is None
    cause = advance_quarter(character, ["supernatural-vampire"])
    assert character["species_data"]["bloodlust"] == 100
    assert character["hunter_heat"] == 100
    assert character["age_quarters"] == 4
    assert character["age_years"] == 1
    assert cause is not None
    assert "Hunters" in cause


def test_species_effects_apply_only_to_vampires():
    human = fresh_character("Ada", "stable", [])
    apply_choice(human, {"effects": {}, "flags": {}, "species_effects": {"bloodlust": -20, "hunter_heat": 30}})
    assert human["hunter_heat"] == 0
    vampire = fresh_character("Ada", "stable", [], species="vampire", clan="Red Ledger")
    apply_choice(vampire, {"effects": {}, "flags": {}, "species_effects": {"bloodlust": 20, "masquerade": -10}})
    assert vampire["species_data"]["clan"] == "Red Ledger"
    assert vampire["species_data"]["bloodlust"] == 40
    assert vampire["species_data"]["masquerade"] == 62


def test_full_moon_with_low_control_raises_hunter_heat():
    character = fresh_character("Ada", "stable", [], species="lycanthrope", subtype="wolf")
    set_age(character, 19)
    character["species_data"]["control"] = 20
    character["hunter_heat"] = 0
    reputation = character["stats"]["reputation"]
    health = character["stats"]["health"]
    cause = advance_quarter(character, [])
    assert character["age_quarters"] == 20
    assert character["age_years"] == 5
    assert character["species_data"]["moon"] == 100
    assert character["hunter_heat"] == 16
    assert character["stats"]["reputation"] < reputation
    assert character["stats"]["health"] < health
    assert character["species_data"]["control"] == 14
    assert cause is None


def test_high_notoriety_year_raises_hunter_heat():
    character = fresh_character("Ada", "stable", [], species="witch")
    character["species_data"]["notoriety"] = 80
    character["species_data"]["mana"] = 30
    character["hunter_heat"] = 4
    assert advance_quarter(character, []) is None
    assert character["hunter_heat"] == 4
    assert character["species_data"]["mana"] == 33
    for _ in range(3):
        assert advance_quarter(character, []) is None
    assert character["hunter_heat"] == 12
    assert character["species_data"]["mana"] == 42


def test_moon_and_notoriety_effects_stay_on_their_species():
    lycan = fresh_character("Ada", "stable", [], species="lycanthrope", subtype="stag")
    apply_choice(lycan, {"effects": {}, "flags": {}, "species_effects": {"control": -10, "mana": 20, "hunter_heat": 3}})
    assert lycan["species_data"]["subtype"] == "stag"
    assert lycan["species_data"]["control"] == 54
    assert "mana" not in lycan["species_data"]
    assert lycan["hunter_heat"] == 3
    witch = fresh_character("Ada", "stable", [], species="witch")
    apply_choice(witch, {"effects": {}, "flags": {}, "species_effects": {"notoriety": 20, "moon": 40}})
    assert witch["species_data"]["notoriety"] == 32
    assert "moon" not in witch["species_data"]


def test_migrate_fills_lycan_and_witch_meters():
    lycan = _migrate_character({"name": "Ada", "age_years": 16, "stats": {}, "flags": {}, "species": "lycanthrope"})
    assert lycan["species_data"]["subtype"] in LYCAN_SUBTYPES
    assert lycan["species_data"]["pack"] is None
    assert lycan["species_data"]["last_power_age"] is None
    witch = _migrate_character(
        {"name": "Bea", "age_years": 20, "stats": {}, "flags": {}, "species": "witch", "species_data": {"notoriety": 140}}
    )
    assert witch["species_data"]["notoriety"] == 100
    assert witch["species_data"]["coven"] is None
    assert witch["hunter_heat"] == 0


def test_sanitize_rejects_a_thin_event():
    character = fresh_character("Ada", "stable", [])
    assert _sanitize_event({"title": "Only", "narrative": "One.", "choices": [{"label": "A", "outcome": "B"}]}, character) is None


def test_four_quarters_are_one_year():
    character = fresh_character("Ada", "stable", [])
    for _ in range(4):
        assert advance_quarter(character, []) is None
    assert character["age_quarters"] == 4
    assert character["age_years"] == 1
    assert character["age_months"] == 0


def test_adult_paths_wait_until_seventy_two_quarters():
    character = fresh_character("Ada", "stable", ["career-medicine"])
    character["flags"]["honesty"] = 20
    character["flags"]["ambition"] = 70
    character["flags"]["nature"] = 70
    character["flags"]["aggression"] = 70
    set_age(character, 71)
    closed = compute_paths(character, ["career-medicine"])
    assert "gray_market" not in closed
    assert "career:medicine" not in closed
    set_age(character, 72)
    opened = compute_paths(character, ["career-medicine"])
    assert "gray_market" in opened
    assert "career:medicine" in opened


def test_old_age_death_stays_in_a_human_span():
    elder = fresh_character("Bea", "stable", [])
    set_age(elder, 70 * 4)
    elder["stats"]["health"] = 70
    while elder["stats"]["health"] > 0 and elder["age_quarters"] < 120 * 4:
        advance_quarter(elder, [])
    assert 100 <= elder["age_years"] < 110
