from server import (
    _migrate_character,
    _sanitize_event,
    advance_life,
    apply_choice,
    apply_owned_grants,
    compute_paths,
    fresh_character,
    marks_for_life,
    save_is_incompatible,
)


def test_marks_formula():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 70
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
    character["age_years"] = 16
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
    character["age_years"] = 22
    paths = compute_paths(character, ["career-medicine"])
    assert "career:medicine" in paths


def test_sanitize_clamps_and_drops_garbage():
    character = fresh_character("Ada", "stable", [])
    character["age_years"] = 30
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
    character["age_years"] = 30
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
    cause = advance_life(character, ["supernatural-vampire"])
    assert character["species_data"]["bloodlust"] == 100
    assert character["hunter_heat"] == 100
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


def test_sanitize_rejects_a_thin_event():
    character = fresh_character("Ada", "stable", [])
    assert _sanitize_event({"title": "Only", "narrative": "One.", "choices": [{"label": "A", "outcome": "B"}]}, character) is None
