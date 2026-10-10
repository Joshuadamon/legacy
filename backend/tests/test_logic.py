from server import (
    _migrate_character,
    _sanitize_event,
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


def test_sanitize_rejects_a_thin_event():
    character = fresh_character("Ada", "stable", [])
    assert _sanitize_event({"title": "Only", "narrative": "One.", "choices": [{"label": "A", "outcome": "B"}]}, character) is None
