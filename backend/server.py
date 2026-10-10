"""LEGACY API — one life per turn, from birth to the heir who continues it."""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent / ".env")

MONGO_URL = os.environ.get("MONGO_URL", "memory://")
DB_NAME = os.environ.get("DB_NAME", "legacy")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
STARTING_MARKS = 250

logger = logging.getLogger("legacy")
logging.basicConfig(level=logging.INFO)

STAT_KEYS = ("health", "happiness", "smarts", "looks", "money", "reputation", "family")
FLAG_KEYS = (
    "morality",
    "honesty",
    "discipline",
    "aggression",
    "addiction",
    "faith",
    "nature",
    "ambition",
    "charisma",
    "resilience",
)
METER_STATS = tuple(key for key in STAT_KEYS if key != "money")

CHILD_NAMES = (
    "Mina",
    "Eli",
    "Ruth",
    "Sam",
    "Nora",
    "Jude",
    "Ivy",
    "Cal",
    "Pearl",
    "Theo",
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(value)))


def clamp_money(value: int) -> int:
    return max(-1_000_000, min(100_000_000, int(value)))


def clamp_delta(value: Any, limit: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(-limit, min(limit, number))


def clean_name(name: str | None, fallback: str = "Unnamed") -> str:
    text = " ".join(str(name or "").split())
    text = "".join(ch for ch in text if ch.isprintable())
    text = text[:40].strip()
    return text or fallback


def stage_for(age: int) -> str:
    if age < 3:
        return "infant"
    if age < 13:
        return "child"
    if age < 18:
        return "teen"
    if age < 30:
        return "young_adult"
    if age < 60:
        return "adult"
    return "elder"


def public_doc(doc: dict | None) -> dict | None:
    if not doc:
        return None
    copied = dict(doc)
    copied.pop("_id", None)
    return copied


# --- catalog -----------------------------------------------------------------

BACKGROUNDS: dict[str, dict[str, Any]] = {
    "stable": {
        "label": "A steady house",
        "blurb": "Two adults, a kitchen table, and rules that mostly held.",
        "stats": {
            "health": 70,
            "happiness": 64,
            "smarts": 55,
            "looks": 50,
            "money": 400,
            "reputation": 48,
            "family": 70,
        },
        "flags": {
            "morality": 55,
            "honesty": 58,
            "discipline": 52,
            "aggression": 28,
            "addiction": 8,
            "faith": 40,
            "nature": 34,
            "ambition": 46,
            "charisma": 45,
            "resilience": 50,
        },
    },
    "poverty": {
        "label": "Thin walls",
        "blurb": "The bills arrived before the groceries did.",
        "stats": {
            "health": 58,
            "happiness": 42,
            "smarts": 52,
            "looks": 46,
            "money": 40,
            "reputation": 30,
            "family": 55,
        },
        "flags": {
            "morality": 48,
            "honesty": 50,
            "discipline": 44,
            "aggression": 36,
            "addiction": 14,
            "faith": 36,
            "nature": 30,
            "ambition": 58,
            "charisma": 42,
            "resilience": 68,
        },
    },
    "foster": {
        "label": "Someone else's spare room",
        "blurb": "You learned early how to pack a bag without being asked.",
        "stats": {
            "health": 60,
            "happiness": 40,
            "smarts": 54,
            "looks": 48,
            "money": 80,
            "reputation": 34,
            "family": 28,
        },
        "flags": {
            "morality": 46,
            "honesty": 42,
            "discipline": 40,
            "aggression": 38,
            "addiction": 16,
            "faith": 28,
            "nature": 32,
            "ambition": 52,
            "charisma": 48,
            "resilience": 72,
        },
    },
    "wealthy": {
        "label": "A house with a gate",
        "blurb": "Comfort was assumed. So was the invoice for it.",
        "stats": {
            "health": 74,
            "happiness": 60,
            "smarts": 62,
            "looks": 64,
            "money": 8000,
            "reputation": 58,
            "family": 48,
        },
        "flags": {
            "morality": 42,
            "honesty": 40,
            "discipline": 48,
            "aggression": 24,
            "addiction": 18,
            "faith": 30,
            "nature": 22,
            "ambition": 64,
            "charisma": 60,
            "resilience": 36,
        },
    },
    "rural_faith": {
        "label": "Sunday and the back field",
        "blurb": "The town knew your people, and the church knew your absences.",
        "stats": {
            "health": 68,
            "happiness": 58,
            "smarts": 50,
            "looks": 48,
            "money": 250,
            "reputation": 52,
            "family": 74,
        },
        "flags": {
            "morality": 62,
            "honesty": 60,
            "discipline": 58,
            "aggression": 26,
            "addiction": 6,
            "faith": 74,
            "nature": 70,
            "ambition": 40,
            "charisma": 44,
            "resilience": 60,
        },
    },
}

STORE_PACKS: list[dict[str, Any]] = [
    {
        "id": "career-medicine",
        "category": "career",
        "name": "White Coat",
        "blurb": "Hospitals will hear you out. The hours are long, and the mistakes have names.",
        "cost": 150,
        "grants": {"careers": ["medicine"]},
    },
    {
        "id": "career-law",
        "category": "career",
        "name": "The Bar",
        "blurb": "A license to argue for a living. Someone still has to pay the retainer.",
        "cost": 150,
        "grants": {"careers": ["law"]},
    },
    {
        "id": "career-press",
        "category": "career",
        "name": "The Byline",
        "blurb": "Newsrooms will take a draft from you. They will also take the evening.",
        "cost": 150,
        "grants": {"careers": ["journalism"]},
    },
    {
        "id": "skill-charm",
        "category": "skills",
        "name": "Silver Tongue",
        "blurb": "People let you finish the sentence. That is not the same as trusting you.",
        "cost": 100,
        "grants": {"flags": {"charisma": 8}},
    },
    {
        "id": "skill-habit",
        "category": "skills",
        "name": "Iron Habit",
        "blurb": "You keep the hours you set. The people around you may not thank you.",
        "cost": 100,
        "grants": {"flags": {"discipline": 8}},
    },
    {
        "id": "skill-books",
        "category": "skills",
        "name": "Quiet Books",
        "blurb": "You retain what you read. It does not make the room kinder.",
        "cost": 100,
        "grants": {"stats": {"smarts": 6}},
    },
    {
        "id": "cosmetic-coat",
        "category": "cosmetic",
        "name": "Black Wool Coat",
        "blurb": "It does not change the weather. It changes who holds the door.",
        "cost": 50,
        "grants": {"cosmetic": "Black Wool Coat"},
    },
    {
        "id": "cosmetic-ring",
        "category": "cosmetic",
        "name": "Signet Ring",
        "blurb": "A small claim that your name was chosen, not issued.",
        "cost": 50,
        "grants": {"cosmetic": "Signet Ring"},
    },
    {
        "id": "cosmetic-scar",
        "category": "cosmetic",
        "name": "A Story About the Scar",
        "blurb": "You pick the version. Listeners rarely ask for the other one.",
        "cost": 50,
        "grants": {"cosmetic": "A practiced story"},
    },
    {
        "id": "lifestyle-lease",
        "category": "lifestyle",
        "name": "A City Lease",
        "blurb": "Your name on a door in a place that does not sleep.",
        "cost": 150,
        "grants": {"stats": {"happiness": 4}, "flags": {"ambition": 4}},
    },
    {
        "id": "lifestyle-cabin",
        "category": "lifestyle",
        "name": "The Cabin Deed",
        "blurb": "A key, a stove, and fewer people who know your business.",
        "cost": 150,
        "grants": {"flags": {"nature": 10}, "stats": {"family": 3}},
    },
    {
        "id": "supernatural-vampire",
        "category": "supernatural",
        "name": "The Thirst",
        "blurb": "A later child of your line may be born into the blood. The thirst itself is not awake yet.",
        "cost": 500,
        "grants": {"species": ["vampire"]},
    },
    {
        "id": "supernatural-lycanthrope",
        "category": "supernatural",
        "name": "The Moon",
        "blurb": "A later child may answer to the moon. The shift is not yours to call yet.",
        "cost": 560,
        "grants": {"species": ["lycanthrope"]},
    },
    {
        "id": "supernatural-witch",
        "category": "supernatural",
        "name": "The Craft",
        "blurb": "A later child may keep a working. The coven does not know your name yet.",
        "cost": 440,
        "grants": {"species": ["witch"]},
    },
]

PACKS_BY_ID = {pack["id"]: pack for pack in STORE_PACKS}
CATEGORIES = ("career", "skills", "cosmetic", "lifestyle", "supernatural")


def choice(
    label: str,
    outcome: str,
    effects: dict[str, int] | None = None,
    flags: dict[str, int] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "label": label,
        "outcome": outcome,
        "effects": effects or {},
        "flags": flags or {},
    }
    for key in ("milestone", "fatal", "child_born", "child_name"):
        if extra.get(key) is not None:
            row[key] = extra[key]
    return row


def event(title: str, narrative: str, choices: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": title, "narrative": narrative, "choices": choices}


EVENTS: dict[str, list[dict[str, Any]]] = {
    "infant": [
        event(
            "First winter",
            "The house learns your cry. Someone always comes. Someone is always tired.",
            [
                choice("Settle when held", "You take the warmth that is offered.", {"happiness": 4, "family": 3}, {"resilience": 1}),
                choice("Stay restless", "Sleep is a negotiation you have not agreed to.", {"health": -2}, {"ambition": 1}),
            ],
        ),
        event(
            "A name said often",
            "They use your name until it sticks. The tone depends on the day.",
            [
                choice("Turn toward the voice", "You start to know which footsteps are safe.", {"happiness": 3, "family": 2}),
                choice("Watch the door", "You learn the room before you learn the people.", {"smarts": 2}, {"resilience": 2}),
            ],
        ),
        event(
            "Fever night",
            "A small heat takes you. The kitchen light stays on.",
            [
                choice("Let them nurse it", "The fever breaks by morning. So does someone's patience.", {"health": 4, "family": 2}),
                choice("Fight the blankets", "You come through it stubborn.", {"health": 1}, {"resilience": 3}),
            ],
        ),
    ],
    "child": [
        event(
            "The lunch table",
            "There is a seat that is always left, and it is next to you. Today someone sits.",
            [
                choice("Share what you have", "They remember the offer longer than the food.", {"happiness": 3, "family": 2}, {"morality": 2}),
                choice("Keep your head down", "The hour ends. That is a kind of victory.", {"happiness": -1}, {"resilience": 2}),
                choice("Make them laugh", "The table shifts. You did that.", {"happiness": 4}, {"charisma": 3}),
            ],
        ),
        event(
            "A broken thing",
            "Something in the house is in pieces and everyone can hear it in the silence after.",
            [
                choice("Say it was you", "The consequence is ordinary and yours.", {"family": 2}, {"honesty": 4, "discipline": 1}),
                choice("Say nothing", "Someone else takes the look. You keep the quiet.", {"happiness": -3}, {"honesty": -4}),
                choice("Blame the dog", "It works. The dog does not argue.", {"happiness": 1}, {"honesty": -3, "morality": -2}),
            ],
        ),
        event(
            "The long way home",
            "School lets out. The short way is crowded. The long way is yours.",
            [
                choice("Take the long way", "You learn the names of trees nobody asked about.", {"happiness": 2}, {"nature": 3}),
                choice("Walk with the group", "You practice being included.", {"happiness": 3}, {"charisma": 2}),
                choice("Stay late on purpose", "An empty hallway is easier than a full street.", {"smarts": 2}, {"discipline": 2}),
            ],
        ),
        event(
            "Report card",
            "The paper is thin and somehow heavy. An adult is waiting to read it over your shoulder.",
            [
                choice("Hand it over", "The talk is about effort, which is not the same as pride.", {"family": 2}, {"honesty": 2, "discipline": 2}),
                choice("Forge a brighter one", "The ink is wrong if anyone looks closely. They don't.", {"happiness": 2}, {"honesty": -5, "ambition": 2}),
                choice("Lose it in a puddle", "Accidents happen. This one had help.", {"happiness": -1}, {"honesty": -2}),
            ],
        ),
        event(
            "A smaller kid",
            "Someone is being made small behind the building. They see you see it.",
            [
                choice("Step in", "You leave with a shove and a story. So do they, a better one.", {"health": -4, "reputation": 4}, {"morality": 4, "aggression": 2}),
                choice("Get an adult", "It stops. You are not the hero they tell it as.", {"reputation": 2}, {"honesty": 2, "discipline": 2}),
                choice("Keep walking", "The sound follows you further than the block.", {"happiness": -4}, {"morality": -4}),
            ],
        ),
        event(
            "Sunday rules",
            "There is a place you are expected, and a version of you that is expected inside it.",
            [
                choice("Go and sit still", "The hour is long. Belonging is a chair you don't pick.", {"family": 3}, {"faith": 3, "discipline": 2}),
                choice("Skip it for the creek", "Your shoes come home wet. Your name comes home first.", {"happiness": 3}, {"faith": -3, "nature": 3}),
                choice("Go and ask a hard question", "The answer is a pamphlet. You keep the question.", {"smarts": 2}, {"faith": 1, "ambition": 1}),
            ],
        ),
        event(
            "Allowance",
            "A few bills, counted twice. The corner store already knows what you want.",
            [
                choice("Save it in a book", "The book gets thicker. So does the wanting.", {"money": 15}, {"discipline": 3}),
                choice("Spend it on someone else", "Their surprise is worth more than the thing.", {"happiness": 4, "money": -5}, {"morality": 2, "charisma": 1}),
                choice("Lose it on purpose to a dare", "You buy a reputation you cannot return.", {"money": -10, "reputation": 2}, {"discipline": -2}),
            ],
        ),
        event(
            "The spare key",
            "You are trusted with a key before you are trusted with an explanation.",
            [
                choice("Use it only as told", "Trust, it turns out, is a habit.", {"family": 3}, {"honesty": 2, "discipline": 2}),
                choice("Bring a friend through", "The house feels smaller with a witness.", {"happiness": 2}, {"honesty": -3}),
                choice("Copy the pattern in your head", "You could come and go. You mostly don't.", {"smarts": 2}, {"ambition": 2}),
            ],
        ),
    ],
    "teen": [
        event(
            "A ride after dark",
            "Someone older has a car and a plan that is mostly 'not here'.",
            [
                choice("Go, and be home by midnight", "You make the hour. Barely. It counts.", {"happiness": 4}, {"discipline": 2, "charisma": 2}),
                choice("Go, and don't watch the clock", "Morning is a rumor told by a furious adult.", {"happiness": 2, "family": -4}, {"discipline": -4, "addiction": 2}),
                choice("Stay in", "The group chat proceeds without you. The house is quiet.", {"happiness": -2, "family": 2}, {"discipline": 2}),
            ],
        ),
        event(
            "First wage",
            "A shift ends and the envelope is thinner than the speech about hard work.",
            [
                choice("Give half at home", "The kitchen is less tense for a week.", {"money": 40, "family": 4}, {"morality": 2}),
                choice("Keep it", "You learn what your time is worth to you.", {"money": 80}, {"ambition": 3, "honesty": -1}),
                choice("Quit before the second week", "The speech was worse than the work.", {"happiness": 2, "money": 20}, {"discipline": -3}),
            ],
        ),
        event(
            "The party",
            "A house with the adults gone. The courage in the kitchen is not courage.",
            [
                choice("Nurse one and leave", "You were there. You were also gone.", {"happiness": 2}, {"discipline": 2}),
                choice("Match the room", "The night smears. So does a promise you made yourself.", {"happiness": 3, "health": -4}, {"addiction": 6, "discipline": -3}),
                choice("Be the one who gets people home", "Nobody writes songs about it.", {"reputation": 3, "happiness": 1}, {"morality": 3, "resilience": 2}),
            ],
        ),
        event(
            "Someone looks back",
            "A person at school starts waiting where you walk. It is not an accident.",
            [
                choice("Walk with them", "The route gets longer on purpose.", {"happiness": 6}, {"charisma": 3}),
                choice("Keep it a nod", "Wanting is easier when it stays theoretical.", {"happiness": -1}, {"discipline": 1}),
                choice("Make it a show", "Other people hear about it before they do.", {"reputation": 2, "happiness": 1}, {"honesty": -2}),
            ],
        ),
        event(
            "The application",
            "A form asks who you are going to be. The cursor blinks like it knows better.",
            [
                choice("Tell the flattering version", "It is not quite a lie. It is a wish with a deadline.", {"smarts": 2}, {"ambition": 4, "honesty": -1}),
                choice("Tell the true version", "The truth is plainer and harder to reject.", {"reputation": 2}, {"honesty": 4, "resilience": 1}),
                choice("Leave it blank", "A blank form is also a plan.", {"happiness": -2}, {"ambition": -3, "nature": 2}),
            ],
        ),
        event(
            "A shove in the lot",
            "Someone wants an audience. You are convenient.",
            [
                choice("Leave", "Pride is cheaper than an emergency room.", {"happiness": -2}, {"discipline": 2, "aggression": -2}),
                choice("Swing", "You both look worse after. The story picks a winner anyway.", {"health": -8, "reputation": -2}, {"aggression": 6, "morality": -2}),
                choice("Talk them down", "It works until it doesn't. Today it works.", {"reputation": 3}, {"charisma": 3, "honesty": 1}),
            ],
        ),
    ],
    "young_adult": [
        event(
            "Rent",
            "The landlord stops knocking and starts leaving notes. The notes are not poetry.",
            [
                choice("Pay it", "The month survives. Your account looks haunted.", {"money": -350, "happiness": 2}, {"discipline": 2}),
                choice("Negotiate a week", "You buy time with a voice that does not shake.", {"money": -150, "happiness": -1}, {"charisma": 2}),
                choice("Disappear for a few days", "The problem keeps your forwarding address.", {"happiness": -4, "reputation": -3}, {"honesty": -3, "resilience": 1}),
            ],
        ),
        event(
            "A shift that sticks",
            "They offer you the same hours next month, which is their version of a future.",
            [
                choice("Take the hours", "Routine is a kind of shelter.", {"money": 280}, {"discipline": 3, "ambition": 1}),
                choice("Ask for better ones", "They say they'll think about it. They might.", {"money": 120}, {"ambition": 3, "charisma": 2}),
                choice("Turn it down", "Freedom and a low balance look similar on paper.", {"happiness": 2, "money": -40}, {"ambition": -2, "nature": 2}),
            ],
        ),
        event(
            "The roommate",
            "The person on the lease with you has a different definition of 'shared'.",
            [
                choice("Write it down", "A list on the fridge prevents a religion of resentment.", {"happiness": 2, "family": 1}, {"honesty": 3, "discipline": 2}),
                choice("Eat the loss", "You keep the peace and lose the leftovers.", {"happiness": -3, "money": -40}, {"morality": 1}),
                choice("Move out in a weekend", "The boxes fit. The friendship does not.", {"happiness": -2, "money": -200}, {"resilience": 3}),
            ],
        ),
        event(
            "A number for your company",
            "Someone names a figure for your evenings. It is more than the rent, and less than a straight answer.",
            [
                choice("Leave the number on the table", "You walk home ordinary and unpaid.", {"happiness": 1}, {"honesty": 3, "morality": 2}),
                choice("Agree, quietly", "The money arrives. So does a private you don't introduce.", {"money": 700, "reputation": -8, "happiness": -4}, {"morality": -4, "resilience": 1}),
                choice("Tell them you are not for sale", "They laugh. You don't. The laugh dies first.", {"reputation": 3, "happiness": 3}, {"charisma": 2, "ambition": 1}),
            ],
        ),
        event(
            "Someone stays the night",
            "It becomes a week, then a toothbrush, then a question neither of you scheduled.",
            [
                choice("Ask them to stay", "The apartment learns a second set of keys.", {"happiness": 6, "family": 3}, {"charisma": 1}),
                choice("Keep it casual", "Casual is a word people use when they are afraid of the other ones.", {"happiness": 2}, {"honesty": -1}),
                choice("End it cleanly", "Clean is relative. Kind is the part you manage.", {"happiness": -4}, {"honesty": 3, "resilience": 2}),
            ],
        ),
        event(
            "The habit",
            "You told yourself this would be the week it stopped. The week has other plans.",
            [
                choice("Tell one person", "Saying it out loud makes it harder to decorate.", {"happiness": 2, "health": 2}, {"addiction": -6, "honesty": 3}),
                choice("Hide it better", "You get skilled at a thing that does not love you back.", {"happiness": -2}, {"addiction": 6, "honesty": -3}),
                choice("Miss what you promised", "A chair stays empty where you were supposed to be.", {"money": -80, "reputation": -3}, {"discipline": -4, "addiction": 3}),
            ],
        ),
        event(
            "A cousin's van",
            "He has addresses and a rate. He will not say what the crates are. He will say what they pay.",
            [
                choice("Decline", "Family dinners get a little formal. Your name stays off the route.", {"family": -2}, {"honesty": 3, "morality": 3}),
                choice("Drive and don't ask", "The envelope is thick. Your questions get thin.", {"money": 900, "reputation": -4}, {"honesty": -6, "morality": -5, "ambition": 2}),
                choice("Ask until he lies", "The lie is clumsy. You still have to decide what to do with it.", {"smarts": 2}, {"honesty": 1, "ambition": 1}),
            ],
        ),
        event(
            "A class you pay for",
            "Nights, a plastic chair, a subject that might become a door.",
            [
                choice("Finish the term", "You are tired in a way that looks like progress.", {"money": -200, "smarts": 5}, {"discipline": 4, "ambition": 2}),
                choice("Drop it", "The refund is partial. So is the relief.", {"money": -40, "happiness": 1}, {"discipline": -2}),
                choice("Cheat the last exam", "The grade is pretty. You know what it cost.", {"smarts": -1}, {"honesty": -5, "ambition": 2}),
            ],
        ),
    ],
    "adult": [
        event(
            "A child arrives",
            "Someone you have been seeing is pregnant. The timeline points at you, and does not blink.",
            [
                choice(
                    "Take the child into your life",
                    "Your name goes on the form. The nights get shorter and more specific.",
                    {"happiness": 4, "money": -200, "family": 8},
                    {"morality": 3, "discipline": 2},
                    child_born=True,
                    milestone="A child enters the line.",
                ),
                choice(
                    "Support them from a distance",
                    "Money moves. You do not. Both facts are public in a small way.",
                    {"money": -350, "family": 2, "happiness": -2},
                    {"honesty": 1, "morality": -1},
                    child_born=True,
                    milestone="A child is born, and lives mostly elsewhere.",
                ),
                choice("Deny the timeline", "It might hold. It will not feel like it does.", {"reputation": -6, "happiness": -3}, {"honesty": -6, "morality": -4}),
            ],
        ),
        event(
            "The promotion that isn't",
            "They praise your judgment and renew your salary, which is not the same sentence.",
            [
                choice("Stay and get better", "You become undeniable, or you become furniture. Not this year.", {"money": 200}, {"discipline": 3, "ambition": 2}),
                choice("Leave for a rival", "The new office has your name on a worse chair and a better number.", {"money": 500, "reputation": 2}, {"ambition": 4}),
                choice("Say what you are worth", "The room goes polite. Polite is not a no.", {"money": 150, "reputation": 2}, {"charisma": 3, "honesty": 2}),
            ],
        ),
        event(
            "A parent falters",
            "The person who raised you needs a kind of help they once swore they would never ask for.",
            [
                choice("Move them closer", "Your square footage becomes a family plot.", {"money": -300, "happiness": -1, "family": 8}, {"morality": 4, "discipline": 2}),
                choice("Send money, not days", "The check clears. The phone calls get shorter.", {"money": -400, "family": 2}, {"morality": 1}),
                choice("Tell them you can't", "It is true and it is ugly. Both can be accurate.", {"happiness": -4, "family": -6}, {"honesty": 2, "resilience": 2}),
            ],
        ),
        event(
            "The affair of attention",
            "Someone who is not yours starts saving you a seat. You start arriving early enough to take it.",
            [
                choice("Stop", "You keep the life you already named.", {"happiness": -2, "family": 3}, {"honesty": 4, "morality": 3}),
                choice("Let it become something", "Two houses learn how to lie about a calendar.", {"happiness": 4, "family": -8, "reputation": -4}, {"honesty": -6, "morality": -4}),
                choice("Tell your person first", "The sentence costs more than the secret did.", {"happiness": -6, "family": -2}, {"honesty": 6, "resilience": 3}),
            ],
        ),
        event(
            "A debt with your name",
            "An old balance finds a new letterhead. They are patient in the way of institutions.",
            [
                choice("Pay it down hard", "Rice and quiet for a season. The number shrinks.", {"money": -600, "happiness": -2}, {"discipline": 4, "honesty": 2}),
                choice("Minimums forever", "You rent your own past.", {"money": -80, "happiness": -1}, {"discipline": -2}),
                choice("Ignore the envelope", "Interest is a quiet animal. It eats.", {"money": -40, "reputation": -3}, {"honesty": -3, "resilience": -1}),
            ],
        ),
        event(
            "The town you left",
            "A funeral, or a wedding — the invitation does not care which grudge you packed.",
            [
                choice("Go home", "You remember the roads. The roads remember your car.", {"happiness": 2, "family": 5, "money": -150}, {"faith": 1}),
                choice("Send flowers and a sentence", "It is received. It is not the same.", {"money": -60, "family": 1}, {"honesty": 1}),
                choice("Pretend it missed you", "Your absence becomes a character in someone else's story.", {"family": -4}, {"honesty": -2, "ambition": 1}),
            ],
        ),
        event(
            "Layoff season",
            "A meeting with no agenda. A box that is already the right size.",
            [
                choice("Take the package and job hunt", "You become a professional of follow-ups.", {"money": 400, "happiness": -3}, {"resilience": 4, "ambition": 2}),
                choice("Burn the exit interview", "It feels like weather. It is a story they will retell.", {"happiness": 2, "reputation": -4}, {"aggression": 4, "honesty": 2}),
                choice("Ask to stay for less", "Pride negotiates. It does not win.", {"money": 100, "happiness": -4}, {"discipline": 2, "ambition": -2}),
            ],
        ),
        event(
            "A second child, or not",
            "The question arrives without a meeting. The apartment has an opinion.",
            [
                choice(
                    "Yes",
                    "Another name to answer to in the dark.",
                    {"happiness": 3, "money": -250, "family": 6},
                    {"faith": 1, "discipline": 1},
                    child_born=True,
                    milestone="Another child joins the house.",
                ),
                choice("Not now", "The not-now becomes its own room you walk past.", {"happiness": 1}, {"discipline": 2, "ambition": 1}),
                choice("Never, and say so", "Clarity is a kindness with a sharp edge.", {"happiness": -1, "family": 1}, {"honesty": 4}),
            ],
        ),
        event(
            "The friend who slips",
            "Someone you love is disappearing in installments. They still make the joke first.",
            [
                choice("Show up uninvited", "They are angry, then they are not, then they are tired.", {"happiness": -1, "family": 2}, {"morality": 3, "resilience": 2}),
                choice("Match them", "Solidarity is a poor word for what this is.", {"health": -4, "happiness": -2}, {"addiction": 5, "morality": -2}),
                choice("Step back", "You keep yourself. You may not keep them.", {"happiness": -3}, {"discipline": 2, "honesty": 1}),
            ],
        ),
        event(
            "A small bet on yourself",
            "An idea, a lease, a thing with your name that is not a job someone else owns.",
            [
                choice("Start it lean", "The first month is all hours and no myth.", {"money": -500, "happiness": 3}, {"ambition": 5, "discipline": 2}),
                choice("Wait for a safer year", "Safer years have a way of staying theoretical.", {"happiness": -1}, {"discipline": 2, "ambition": -2}),
                choice("Take a partner's money", "The dream gets a co-signer and a second opinion.", {"money": 300, "family": -2}, {"ambition": 3, "honesty": 1}),
            ],
        ),
    ],
    "elder": [
        event(
            "The body keeps minutes",
            "Stairs become a negotiation. People begin finishing your stories, badly.",
            [
                choice("Slow down on purpose", "You keep what you can by spending it carefully.", {"health": 2, "happiness": 1}, {"discipline": 2, "resilience": 2}),
                choice("Pretend nothing changed", "The fall is small. The bruise is an editor.", {"health": -6, "happiness": -2}, {"ambition": 1, "discipline": -2}),
                choice("Tell the children the truth", "They look older when you do.", {"family": 4, "happiness": 1}, {"honesty": 3}),
            ],
        ),
        event(
            "What to do with the house",
            "The rooms are larger than the life. Someone has a brochure.",
            [
                choice("Stay until you can't", "The kettle is still yours.", {"happiness": 3, "money": -80}, {"nature": 2, "resilience": 2}),
                choice("Sell and simplify", "An address becomes a suitcase.", {"money": 1200, "family": -2, "happiness": -1}, {"discipline": 2}),
                choice("Put a child's name on the deed", "Love, filed.", {"money": -200, "family": 6}, {"morality": 3}),
            ],
        ),
        event(
            "A wedding in the line",
            "Someone young asks you to sit where the old stories can see you.",
            [
                choice("Give the toast", "You tell one true thing and one kind thing.", {"happiness": 5, "family": 4}, {"charisma": 2, "faith": 1}),
                choice("Attend and stay quiet", "Your presence is the speech.", {"happiness": 3, "family": 3}, {"discipline": 1}),
                choice("Send regrets", "The photographs will have a gap in the shape of you.", {"happiness": -3, "family": -3}, {"honesty": 1}),
            ],
        ),
        event(
            "The doctor does not rush",
            "They use the voice reserved for news that will not improve by hurrying.",
            [
                choice("Treat it", "You buy time at a price the body understands.", {"health": 6, "money": -700, "happiness": -2}, {"discipline": 3, "resilience": 2}),
                choice("Treat the pain, not the plot", "The days get softer and shorter.", {"health": -2, "happiness": 3, "money": -200}, {"faith": 2}),
                choice("Tell no one yet", "You carry it alone for a season.", {"happiness": -4}, {"honesty": -2, "resilience": 2}),
            ],
        ),
        event(
            "Old heat",
            "A grudge from decades ago sits down at the same diner counter.",
            [
                choice("Let it die here", "You both get to finish your coffee.", {"happiness": 3, "reputation": 2}, {"morality": 3, "aggression": -3}),
                choice("Say the thing you saved", "It lands. Nobody is improved. You are lighter.", {"happiness": 1, "reputation": -1}, {"honesty": 4, "aggression": 2}),
                choice("Walk out", "Some doors are still yours to use.", {"happiness": -1}, {"resilience": 2}),
            ],
        ),
        event(
            "Writing it down",
            "A grandchild, or a stranger with a recorder, asks what the years were for.",
            [
                choice("Tell it straight", "The record gets sharper and less flattering.", {"happiness": 2, "reputation": 2}, {"honesty": 4}),
                choice("Tell the version that helps them", "A useful myth is a kind of inheritance.", {"family": 3, "happiness": 2}, {"honesty": -2, "charisma": 2}),
                choice("Say you don't remember", "Some of that is true.", {"happiness": -1}, {"resilience": 1}),
            ],
        ),
        event(
            "Winter, again",
            "{name} counts the people who would notice a dark window. The number is specific.",
            [
                choice("Call someone", "A voice answers. That is the whole miracle.", {"happiness": 4, "family": 3, "health": 1}, {"faith": 1}),
                choice("Sit with it", "The quiet is not empty. It is just quiet.", {"happiness": 1}, {"resilience": 3, "nature": 2}),
                choice("Pretend the phone is enough", "It lights up with nothing you asked for.", {"happiness": -3}, {"honesty": -1}),
            ],
        ),
    ],
}

PATH_EVENTS: dict[str, list[dict[str, Any]]] = {
    "devout": [
        event(
            "They ask you to lead",
            "The room wants a voice on the hard week. Yours is the one they look at.",
            [
                choice("Accept the duty", "Faith becomes a calendar.", {"reputation": 4, "happiness": 2}, {"faith": 4, "discipline": 2}),
                choice("Pray and refuse", "You keep your belief and hand back the microphone.", {"happiness": 2}, {"faith": 2, "honesty": 2}),
                choice("Perform it", "The sermon is lovely. You are not in it.", {"reputation": 3}, {"faith": -3, "honesty": -4}),
            ],
        )
    ],
    "gray_market": [
        event(
            "A cleaner kind of dirty",
            "The money is getting professional. So are the people who would like your name near it.",
            [
                choice("Step out", "You leave richer than you entered and poorer than you pretend.", {"money": -100, "reputation": 2}, {"morality": 4, "honesty": 3}),
                choice("Take a quieter role", "Your hands stay clean. Your cut does not.", {"money": 800, "reputation": -3}, {"honesty": -4, "ambition": 2}),
                choice("Own it", "You stop pretending the crates belong to someone else.", {"money": 1400, "reputation": -8}, {"morality": -6, "ambition": 4, "aggression": 2}),
            ],
        )
    ],
    "performer": [
        event(
            "A room that listens",
            "For a few minutes the noise arranges itself around you.",
            [
                choice("Do the work", "Applause is a weather event. You brought the front.", {"happiness": 6, "money": 200, "reputation": 4}, {"charisma": 3, "ambition": 2}),
                choice("Drink the compliment", "The night becomes about the night.", {"happiness": 2, "health": -2}, {"addiction": 3, "discipline": -2}),
                choice("Walk away at the peak", "They will ask where you went. That is a kind of fame.", {"happiness": 3, "reputation": 2}, {"discipline": 3, "nature": 1}),
            ],
        )
    ],
    "off_grid": [
        event(
            "A plot past the pavement",
            "Someone is selling a piece of ground that does not want a mailbox.",
            [
                choice("Buy in", "You trade square feet of city for a longer view.", {"money": -600, "happiness": 4}, {"nature": 6, "ambition": -1}),
                choice("Visit and leave", "The dirt stays under your nails for a day. That is enough.", {"happiness": 2}, {"nature": 2}),
                choice("Talk a friend into it with you", "Two names on a gate. Twice the weather.", {"money": -300, "family": 3}, {"nature": 4, "charisma": 1}),
            ],
        )
    ],
    "dependent": [
        event(
            "The week it was supposed to stop",
            "You have had this conversation with yourself before. It knows your timing.",
            [
                choice("Ask for a real boundary", "Someone agrees to be inconvenient on your behalf.", {"health": 3, "happiness": 2}, {"addiction": -8, "honesty": 3, "discipline": 2}),
                choice("Switch hiding places", "A new trick for an old devotion.", {"happiness": -2}, {"addiction": 5, "honesty": -3}),
                choice("Let the job go before it fires you", "You choose the order of the loss.", {"money": -200, "reputation": -2}, {"addiction": 2, "resilience": 1}),
            ],
        )
    ],
    "hard_edge": [
        event(
            "A problem that wants a fist",
            "People have started bringing you situations they do not want recorded.",
            [
                choice("Charge for the scare, not the injury", "Fear pays. You keep the line where you can see it.", {"money": 400, "reputation": -3}, {"aggression": 2, "morality": -2, "discipline": 1}),
                choice("Refuse the work", "Your name gets less useful and more your own.", {"money": -50, "reputation": 2}, {"morality": 4, "aggression": -3}),
                choice("Stop measuring", "The story afterward avoids verbs.", {"money": 700, "health": -6, "reputation": -8}, {"aggression": 6, "morality": -6}),
            ],
        )
    ],
    "transactional": [
        event(
            "Terms",
            "The arrangement has regulars now. One of them wants a name to call you in daylight.",
            [
                choice("Keep the terms", "Daylight was never part of the price.", {"money": 500, "happiness": -2}, {"discipline": 2, "honesty": -1}),
                choice("End it", "The money stops. So does a particular kind of flinch.", {"money": -100, "happiness": 4, "reputation": 2}, {"morality": 3, "resilience": 3}),
                choice("Let it become a relationship", "Some of it is real. You will argue later about which part.", {"happiness": 3, "money": 100, "family": 2}, {"honesty": 2, "charisma": 2}),
            ],
        )
    ],
    "pillar": [
        event(
            "They bring you the mess",
            "A neighbor, a niece, a coworker — the story changes, the ask does not.",
            [
                choice("Help without a speech", "Your afternoon becomes theirs.", {"happiness": 2, "family": 3, "money": -40}, {"morality": 3}),
                choice("Help, with conditions", "Kindness acquires a form. It still counts.", {"reputation": 2}, {"discipline": 2, "honesty": 2}),
                choice("Tell them to sort it", "You are not a shelter. You are tired of being mistaken for one.", {"happiness": 1, "family": -2}, {"honesty": 2, "ambition": 1}),
            ],
        )
    ],
    "career_climber": [
        event(
            "The hour nobody wanted",
            "A failure needs an owner before morning. Your name is already near it.",
            [
                choice("Own it and fix it", "By dawn the mess has a smaller footprint and your fingerprints.", {"reputation": 5, "happiness": -2}, {"discipline": 3, "ambition": 3}),
                choice("Share the blame accurately", "Accuracy is unpopular and useful.", {"reputation": 2}, {"honesty": 4}),
                choice("Let a junior wear it", "You sleep. They learn a lesson you assigned.", {"happiness": 1, "reputation": -3}, {"morality": -4, "ambition": 2}),
            ],
        )
    ],
}


def closing_event(character: dict) -> dict[str, Any]:
    name = character["name"]
    age = int(character["age_years"])
    if age >= 105:
        return event(
            "The last account",
            f"{name} has spent the extra years. What remains is the choosing of a last room.",
            [
                choice("Go quietly", "The house notices in the morning.", {"health": -100}, fatal=True),
                choice("Ask for a hand", "Someone is there for the end of the sentence.", {"health": -100, "family": 4}, fatal=True),
            ],
        )
    return event(
        "One more season",
        f"The year offers {name} a narrow continuation, and does not pretend it is wide.",
        [
            choice("Hold on", "You buy a thin year. The body sends an invoice.", {"health": -12, "happiness": 2}, {"resilience": 3}),
            choice("Let the year close", "You stop arguing with the calendar.", {"health": -100}, fatal=True),
        ],
    )


def _pick(options: list[dict[str, Any]], salt: int, banned: set[str]) -> dict[str, Any]:
    if not options:
        raise RuntimeError("empty event pool")
    for offset in range(len(options)):
        item = options[(salt + offset) % len(options)]
        if item["title"] not in banned:
            return item
    return options[salt % len(options)]


def fallback_event(character: dict, history: list[dict[str, Any]], generation: int) -> dict[str, Any]:
    age = int(character["age_years"])
    if age >= 100:
        return closing_event(character)
    stage = character.get("stage") or stage_for(age)
    pool = list(EVENTS.get(stage) or EVENTS["adult"])
    paths = set(character.get("unlocked_paths") or [])
    for path, extras in PATH_EVENTS.items():
        if path in paths:
            pool = extras + pool
    banned = {str(item.get("title")) for item in history[-12:]}
    salt = age * 3 + len(history) * 7 + int(generation)
    chosen = copy.deepcopy(_pick(pool, salt, banned))
    name = character.get("name") or "They"
    chosen["title"] = str(chosen["title"]).replace("{name}", name)
    chosen["narrative"] = str(chosen["narrative"]).replace("{name}", name)
    return chosen


def compute_paths(character: dict, owned_packs: list[str] | None = None) -> list[str]:
    flags = character["flags"]
    stats = character["stats"]
    age = int(character["age_years"])
    paths: list[str] = []
    if age >= 16 and flags["ambition"] >= 60 and flags["discipline"] >= 45:
        paths.append("career_climber")
    if age >= 18 and flags["honesty"] <= 35 and flags["ambition"] >= 55:
        paths.append("gray_market")
    if age >= 13 and flags["faith"] >= 65:
        paths.append("devout")
    if age >= 16 and flags["charisma"] >= 60:
        paths.append("performer")
    if age >= 18 and flags["nature"] >= 60:
        paths.append("off_grid")
    if flags["addiction"] >= 55:
        paths.append("dependent")
    if age >= 18 and flags["aggression"] >= 65:
        paths.append("hard_edge")
    if age >= 22 and flags["morality"] >= 65 and flags["resilience"] >= 55:
        paths.append("pillar")
    if age >= 18 and flags["charisma"] >= 55 and int(stats["money"]) < 200:
        paths.append("transactional")
    if age >= 18:
        owned = set(owned_packs or [])
        for pack in STORE_PACKS:
            if pack["id"] not in owned:
                continue
            for career in pack["grants"].get("careers") or []:
                paths.append(f"career:{career}")
    return paths


def unlocks_from_packs(owned_packs: list[str]) -> dict[str, list[str]]:
    careers: list[str] = []
    cosmetics: list[str] = []
    species: list[str] = []
    owned = set(owned_packs)
    for pack in STORE_PACKS:
        if pack["id"] not in owned:
            continue
        grants = pack["grants"]
        careers.extend(grants.get("careers") or [])
        species.extend(grants.get("species") or [])
        if grants.get("cosmetic"):
            cosmetics.append(str(grants["cosmetic"]))
    return {"careers": careers, "cosmetics": cosmetics, "species": species}


def apply_owned_grants(character: dict, owned_packs: list[str]) -> None:
    applied = set(character.get("applied_grants") or [])
    for pack in STORE_PACKS:
        if pack["id"] not in owned_packs or pack["id"] in applied:
            continue
        grants = pack["grants"]
        for flag, delta in (grants.get("flags") or {}).items():
            if flag in FLAG_KEYS:
                character["flags"][flag] = clamp(character["flags"][flag] + int(delta))
        for stat, delta in (grants.get("stats") or {}).items():
            if stat not in STAT_KEYS:
                continue
            if stat == "money":
                character["stats"][stat] = clamp_money(character["stats"][stat] + int(delta))
            else:
                character["stats"][stat] = clamp(character["stats"][stat] + int(delta))
        applied.add(pack["id"])
    character["applied_grants"] = sorted(applied)


def fresh_character(name: str, background_key: str, owned_packs: list[str]) -> dict[str, Any]:
    background = BACKGROUNDS[background_key]
    character = {
        "name": clean_name(name),
        "background": background["label"],
        "background_key": background_key,
        "age_years": 0,
        "stage": "infant",
        "stats": copy.deepcopy(background["stats"]),
        "flags": copy.deepcopy(background["flags"]),
        "life_log": [],
        "unlocked_paths": [],
        "children": [],
        "partner": None,
        "career": None,
        "business": None,
        "species": "human",
        "species_data": None,
        "applied_grants": [],
    }
    apply_owned_grants(character, owned_packs)
    character["unlocked_paths"] = compute_paths(character, owned_packs)
    return character


def heir_character(parent: dict[str, Any], child: dict[str, Any] | None, given_name: str | None) -> dict[str, Any]:
    """Build the next generation from a child, or from a distant relative when child is None."""
    parent_stats = parent["stats"]
    parent_flags = parent["flags"]
    if child:
        age = max(0, int(parent["age_years"]) - int(child["born_parent_age"]))
        name = child["name"]
        background = f"Raised under {parent['name']}'s roof."
        background_key = "heir"
        money = parent_stats["money"] // 2 if int(parent_stats["money"]) > 0 else 0
    else:
        age = 0
        name = clean_name(given_name, "Rowan Hale")
        background = f"A distant relation of {parent['name']}, with a thinner story and a key to less."
        background_key = "distant"
        money = parent_stats["money"] // 5 if int(parent_stats["money"]) > 0 else 0
    stats = {
        "health": 72 if age < 50 else 60,
        "happiness": clamp(48 + (int(parent_stats["family"]) - 50) // 5),
        "smarts": clamp((int(parent_stats["smarts"]) + 50) // 2),
        "looks": clamp((int(parent_stats["looks"]) + 50) // 2),
        "money": clamp_money(money),
        "reputation": clamp(int(parent_stats["reputation"]) * 6 // 10),
        "family": clamp(36 + int(parent_stats["family"]) // 5),
    }
    flags = {key: clamp((int(parent_flags[key]) + 40) // 2) for key in FLAG_KEYS}
    flags["resilience"] = clamp(flags["resilience"] + 5)
    business = copy.deepcopy(parent["business"]) if parent.get("business") else None
    character = {
        "name": name,
        "background": background,
        "background_key": background_key,
        "age_years": age,
        "stage": stage_for(age),
        "stats": stats,
        "flags": flags,
        "life_log": [f"Continued from {parent['name']}, who died at {parent['age_years']}."],
        "unlocked_paths": [],
        "children": [],
        "partner": None,
        "career": None,
        "business": business,
        "species": "human",
        "species_data": None,
        "applied_grants": [],
    }
    return character


def save_is_incompatible(save: dict[str, Any]) -> bool:
    character = save.get("character") if isinstance(save.get("character"), dict) else {}
    has_needs = "needs" in save or "needs" in character
    has_flags = isinstance(character, dict) and "flags" in character
    return bool(has_needs and not has_flags)


def _migrate_character(character: dict[str, Any]) -> dict[str, Any]:
    character.setdefault("name", "Unnamed")
    character.setdefault("background", BACKGROUNDS["stable"]["label"])
    character.setdefault("background_key", "stable")
    character.setdefault("age_years", 0)
    character["age_years"] = max(0, int(character["age_years"]))
    character["stage"] = stage_for(character["age_years"])
    stats = character.get("stats") if isinstance(character.get("stats"), dict) else {}
    flags = character.get("flags") if isinstance(character.get("flags"), dict) else {}
    base = BACKGROUNDS.get(character["background_key"], BACKGROUNDS["stable"])
    for key in STAT_KEYS:
        stats.setdefault(key, base["stats"][key])
    for key in FLAG_KEYS:
        flags.setdefault(key, base["flags"][key])
    for key in METER_STATS:
        stats[key] = clamp(stats[key])
    stats["reputation"] = clamp(stats["reputation"])
    stats["family"] = clamp(stats["family"])
    stats["money"] = clamp_money(stats["money"])
    for key in FLAG_KEYS:
        flags[key] = clamp(flags[key])
    character["stats"] = stats
    character["flags"] = flags
    character.setdefault("life_log", [])
    character.setdefault("unlocked_paths", [])
    character.setdefault("children", [])
    character.setdefault("partner", None)
    character.setdefault("career", None)
    character.setdefault("business", None)
    character.setdefault("species", "human")
    character.setdefault("species_data", None)
    character.setdefault("applied_grants", [])
    if not isinstance(character["life_log"], list):
        character["life_log"] = []
    if not isinstance(character["children"], list):
        character["children"] = []
    if not isinstance(character["applied_grants"], list):
        character["applied_grants"] = []
    return character


def _migrate_save(save: dict[str, Any]) -> dict[str, Any]:
    save.setdefault("generation", 1)
    save["generation"] = max(1, int(save["generation"]))
    save.setdefault("alive", True)
    save.setdefault("cause_of_death", None)
    save.setdefault("last_outcome", None)
    save.setdefault("history", [])
    save.setdefault("lineage", [])
    save.setdefault("marks_earned", 0)
    save.setdefault("deleted_at", None)
    save.setdefault("created_at", now())
    save.setdefault("updated_at", now())
    if not isinstance(save["history"], list):
        save["history"] = []
    if not isinstance(save["lineage"], list):
        save["lineage"] = []
    if isinstance(save.get("character"), dict):
        save["character"] = _migrate_character(save["character"])
    return save


def _migrate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile.setdefault("marks", STARTING_MARKS)
    profile.setdefault("owned_packs", [])
    profile.setdefault("lives_lived", 0)
    profile.setdefault("deleted_at", None)
    profile.setdefault("created_at", now())
    profile.setdefault("updated_at", now())
    profile["marks"] = max(0, int(profile["marks"]))
    if not isinstance(profile["owned_packs"], list):
        profile["owned_packs"] = []
    profile["lives_lived"] = max(0, int(profile["lives_lived"]))
    return profile


def marks_for_life(character: dict[str, Any], generation: int) -> int:
    reputation = int(character["stats"]["reputation"])
    age = int(character["age_years"])
    return 50 + (reputation // 2) + (age // 2) + int(generation) * 10


def apply_choice(character: dict[str, Any], picked: dict[str, Any]) -> None:
    for stat, delta in (picked.get("effects") or {}).items():
        if stat not in STAT_KEYS:
            continue
        amount = clamp_delta(delta, 50_000 if stat == "money" else 40)
        if stat == "money":
            character["stats"][stat] = clamp_money(int(character["stats"][stat]) + amount)
        else:
            character["stats"][stat] = clamp(int(character["stats"][stat]) + amount)
    for flag, delta in (picked.get("flags") or {}).items():
        if flag not in FLAG_KEYS:
            continue
        character["flags"][flag] = clamp(int(character["flags"][flag]) + clamp_delta(delta, 40))
    if picked.get("child_born") and int(character["age_years"]) >= 16:
        existing = character["children"]
        fallback = CHILD_NAMES[len(existing) % len(CHILD_NAMES)]
        child_name = clean_name(picked.get("child_name"), fallback)
        if child_name == "Unnamed":
            child_name = fallback
        character["children"].append(
            {
                "id": str(uuid.uuid4()),
                "name": child_name,
                "born_parent_age": int(character["age_years"]),
            }
        )
        character["stats"]["family"] = clamp(int(character["stats"]["family"]) + 8)


def advance_life(character: dict[str, Any], owned_packs: list[str]) -> None:
    """Age one year. Species meters will tick here when those packs wake up."""
    character["age_years"] = int(character["age_years"]) + 1
    character["stage"] = stage_for(character["age_years"])
    age = character["age_years"]
    if age >= 70:
        drop = 1 if age < 85 else 3
        character["stats"]["health"] = clamp(int(character["stats"]["health"]) - drop)
    apply_owned_grants(character, owned_packs)
    character["unlocked_paths"] = compute_paths(character, owned_packs)


def trim_log(entries: list[Any], limit: int = 160) -> None:
    if len(entries) > limit:
        del entries[:-limit]


def obituary(save: dict[str, Any]) -> str:
    character = save["character"]
    name = character["name"]
    age = character["age_years"]
    cause = save.get("cause_of_death") or "The record does not say."
    partner = character.get("partner") if isinstance(character.get("partner"), dict) else None
    spouse = ""
    if partner and partner.get("name"):
        status = partner.get("status") or "bound"
        spouse = f" They were {status} to {partner['name']}."
    tail_bits = [str(line) for line in (character.get("life_log") or [])[-2:]]
    tail = " ".join(tail_bits) if tail_bits else "The years were mostly unremarkable, which is its own kind of record."
    return f"{name} died at {age}. {cause}.{spouse} {tail}".strip()


def epitaph(save: dict[str, Any], heir_id: str, heir_name: str) -> dict[str, Any]:
    character = save["character"]
    partner = character.get("partner") if isinstance(character.get("partner"), dict) else None
    return {
        "generation": int(save["generation"]),
        "name": character["name"],
        "years": f"0–{character['age_years']}",
        "cause_of_death": save.get("cause_of_death"),
        "partner": partner.get("name") if partner else None,
        "heir_id": heir_id,
        "heir_name": heir_name,
        "epitaph": obituary(save),
    }


def _sanitize_event(raw: Any, character: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    narrative = str(raw.get("narrative") or "").strip()
    if not title or not narrative:
        return None
    raw_choices = raw.get("choices")
    if not isinstance(raw_choices, list):
        return None
    cleaned: list[dict[str, Any]] = []
    for item in raw_choices[:4]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        outcome = str(item.get("outcome") or "").strip()
        if not label or not outcome:
            continue
        effects: dict[str, int] = {}
        for key, value in (item.get("effects") or {}).items() if isinstance(item.get("effects"), dict) else []:
            if key in STAT_KEYS:
                effects[key] = clamp_delta(value, 50_000 if key == "money" else 40)
        flag_deltas: dict[str, int] = {}
        for key, value in (item.get("flags") or {}).items() if isinstance(item.get("flags"), dict) else []:
            if key in FLAG_KEYS:
                flag_deltas[key] = clamp_delta(value, 40)
        row: dict[str, Any] = {"label": label[:120], "outcome": outcome[:400], "effects": effects, "flags": flag_deltas}
        milestone = item.get("milestone")
        if isinstance(milestone, str) and milestone.strip():
            row["milestone"] = milestone.strip()[:180]
        if item.get("fatal") is True and int(character["age_years"]) >= 8:
            row["fatal"] = True
        if item.get("child_born") is True and int(character["age_years"]) >= 16:
            row["child_born"] = True
            if isinstance(item.get("child_name"), str) and item["child_name"].strip():
                row["child_name"] = clean_name(item["child_name"])
        cleaned.append(row)
    if len(cleaned) < 2:
        return None
    return {"title": title[:120], "narrative": narrative[:1200], "choices": cleaned}


def build_context(character: dict[str, Any], history: list[dict[str, Any]], owned_packs: list[str], generation: int) -> str:
    unlocked = unlocks_from_packs(owned_packs)
    recent = [
        {"age": item.get("age"), "title": item.get("title"), "choice": item.get("choice"), "outcome": item.get("outcome")}
        for item in history[-8:]
    ]
    payload = {
        "generation": generation,
        "name": character["name"],
        "age": character["age_years"],
        "stage": character["stage"],
        "background": character["background"],
        "species": character.get("species") or "human",
        "stats": character["stats"],
        "flags": character["flags"],
        "unlocked_paths": character.get("unlocked_paths") or [],
        "owned_careers": unlocked["careers"],
        "owned_cosmetics": unlocked["cosmetics"],
        "children": character.get("children") or [],
        "partner": character.get("partner"),
        "career": character.get("career"),
        "business": character.get("business"),
        "life_story_so_far": (character.get("life_log") or [])[-24:],
        "recent_years": recent,
    }
    return json.dumps(payload, indent=2, default=str)


SYSTEM_PROMPT = """You write one year of LEGACY, a dark, dry, store-safe life simulator for adults.
Return ONLY a JSON object with this shape:
{
  "title": "short",
  "narrative": "2-4 sentences, second person, concrete, no purple prose",
  "choices": [
    {
      "label": "what the player does",
      "outcome": "one sentence result",
      "effects": {"health": 0, "happiness": 0, "smarts": 0, "looks": 0, "money": 0, "reputation": 0, "family": 0},
      "flags": {"morality": 0, "honesty": 0, "discipline": 0, "aggression": 0, "addiction": 0, "faith": 0, "nature": 0, "ambition": 0, "charisma": 0, "resilience": 0},
      "milestone": null,
      "fatal": false,
      "child_born": false,
      "child_name": null
    }
  ]
}
Rules:
- 2 to 4 choices. Each must change the life in a different direction.
- Continuity: use the name, age, flags, children, and life_story_so_far. Do not contradict them.
- Never repeat a title or situation from recent_years.
- If unlocked_paths or owned_careers are present, let some years branch into them. Ignore empty lists.
- Imply mature trouble (debt, desire, addiction, violence, hustles) by consequence, never by instruction.
- No explicit sexual content. No graphic injury. No real-world how-to for crime, drugs, or self-harm.
- fatal may be true only in late life or when health is already collapsing.
- child_born only if age is at least 18, and at most one choice should offer it.
- Deltas are small integers. Money may move by hundreds, not millions.
- Do not mention Legacy Marks, menus, or that this is a game.
"""


def parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


async def llm_event(character: dict[str, Any], history: list[dict[str, Any]], owned_packs: list[str], generation: int) -> dict[str, Any] | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or ""
    if not api_key:
        return None
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("anthropic SDK is not installed; using the written year deck")
        return None
    client = AsyncAnthropic(api_key=api_key)
    try:
        message = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_context(character, history, owned_packs, generation)}],
        )
    except Exception:
        logger.exception("year generation failed")
        return None
    parts: list[str] = []
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return _sanitize_event(parse_json_object("".join(parts)), character)


async def generate_event(character: dict[str, Any], history: list[dict[str, Any]], owned_packs: list[str], generation: int) -> dict[str, Any]:
    generated = await llm_event(character, history, owned_packs, generation)
    if generated:
        return generated
    return fallback_event(character, history, generation)


# --- storage -----------------------------------------------------------------

class _Result:
    def __init__(self, matched_count: int = 0, modified_count: int = 0, deleted_count: int = 0):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.deleted_count = deleted_count


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(actual, list):
        return expected in actual
    return actual == expected


def _match(doc: dict[str, Any], filt: dict[str, Any]) -> bool:
    for key, expected in filt.items():
        actual = doc.get(key)
        if isinstance(expected, dict) and any(str(op).startswith("$") for op in expected):
            if "$ne" in expected and _contains(actual, expected["$ne"]):
                return False
            if "$gte" in expected and (actual is None or actual < expected["$gte"]):
                return False
            continue
        if not _contains(actual, expected):
            return False
    return True


class MemoryCollection:
    """Small async stand-in so the game runs before MongoDB is installed."""

    def __init__(self) -> None:
        self.docs: list[dict[str, Any]] = []

    async def find_one(self, filt: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self.docs:
            if _match(doc, filt):
                return copy.deepcopy(doc)
        return None

    async def insert_one(self, doc: dict[str, Any]) -> None:
        stored = copy.deepcopy(doc)
        stored.setdefault("_id", str(uuid.uuid4()))
        self.docs.append(stored)

    async def update_one(self, filt: dict[str, Any], update: dict[str, Any]) -> _Result:
        for doc in self.docs:
            if not _match(doc, filt):
                continue
            before = copy.deepcopy(doc)
            for key, value in (update.get("$set") or {}).items():
                doc[key] = copy.deepcopy(value)
            for key, value in (update.get("$inc") or {}).items():
                doc[key] = doc.get(key, 0) + value
            for key, value in (update.get("$addToSet") or {}).items():
                bucket = doc.setdefault(key, [])
                if value not in bucket:
                    bucket.append(copy.deepcopy(value))
            changed = doc != before
            return _Result(matched_count=1, modified_count=1 if changed else 0)
        return _Result()

    async def delete_many(self, filt: dict[str, Any]) -> _Result:
        before = len(self.docs)
        self.docs = [doc for doc in self.docs if not _match(doc, filt)]
        return _Result(deleted_count=before - len(self.docs))


class Database:
    def __init__(self, saves: Any, users: Any, sessions: Any, profiles: Any, exchanges: Any, kind: str):
        self.saves = saves
        self.users = users
        self.sessions = sessions
        self.profiles = profiles
        self.exchanges = exchanges
        self.kind = kind


db: Database | None = None
mongo_client: Any = None


async def connect_db() -> Database:
    global db, mongo_client
    if MONGO_URL.startswith("memory"):
        db = Database(
            MemoryCollection(),
            MemoryCollection(),
            MemoryCollection(),
            MemoryCollection(),
            MemoryCollection(),
            "memory",
        )
        return db
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=4000)
    await mongo_client.admin.command("ping")
    mongo = mongo_client[DB_NAME]
    db = Database(mongo.saves, mongo.users, mongo.sessions, mongo.user_profiles, mongo.session_exchanges, "mongo")
    return db


def require_db() -> Database:
    if db is None:
        raise HTTPException(status_code=500, detail="Database is not connected")
    return db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_db()
    logger.info("LEGACY storage: %s", db.kind if db else "missing")
    yield
    if mongo_client is not None:
        mongo_client.close()


app = FastAPI(title="LEGACY", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api = APIRouter(prefix="/api")


async def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1].strip()
    store = require_db()
    session = await store.sessions.find_one({"session_token": token, "deleted_at": None})
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")
    expires = session.get("expires_at")
    if isinstance(expires, datetime) and expires < now():
        raise HTTPException(status_code=401, detail="Session expired")
    user = await store.users.find_one({"user_id": session["user_id"], "deleted_at": None})
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return public_doc(user) or {}


async def ensure_profile(user_id: str) -> dict[str, Any]:
    store = require_db()
    found = await store.profiles.find_one({"user_id": user_id, "deleted_at": None})
    if found:
        migrated = _migrate_profile(found)
        await store.profiles.update_one(
            {"user_id": user_id, "deleted_at": None},
            {"$set": {"marks": migrated["marks"], "owned_packs": migrated["owned_packs"], "lives_lived": migrated["lives_lived"], "updated_at": now()}},
        )
        return migrated
    created = _migrate_profile(
        {
            "user_id": user_id,
            "marks": STARTING_MARKS,
            "owned_packs": [],
            "lives_lived": 0,
            "deleted_at": None,
            "created_at": now(),
            "updated_at": now(),
        }
    )
    await store.profiles.insert_one(created)
    return created


def profile_view(profile: dict[str, Any]) -> dict[str, Any]:
    owned = list(profile.get("owned_packs") or [])
    return {
        "user_id": profile["user_id"],
        "marks": int(profile["marks"]),
        "owned_packs": owned,
        "lives_lived": int(profile["lives_lived"]),
        "unlocks": unlocks_from_packs(owned),
    }


async def load_active_save(user_id: str) -> dict[str, Any] | None:
    store = require_db()
    found = await store.saves.find_one({"user_id": user_id, "deleted_at": None})
    return found


async def persist_save(save: dict[str, Any]) -> None:
    store = require_db()
    save["updated_at"] = now()
    await store.saves.update_one(
        {"user_id": save["user_id"], "deleted_at": None},
        {
            "$set": {
                "generation": save["generation"],
                "alive": save["alive"],
                "cause_of_death": save.get("cause_of_death"),
                "character": save["character"],
                "current_event": save.get("current_event"),
                "last_outcome": save.get("last_outcome"),
                "history": save.get("history") or [],
                "lineage": save.get("lineage") or [],
                "marks_earned": int(save.get("marks_earned") or 0),
                "updated_at": save["updated_at"],
            }
        },
    )


async def repair_save(save: dict[str, Any], owned_packs: list[str]) -> dict[str, Any] | None:
    if save_is_incompatible(save):
        store = require_db()
        await store.saves.update_one(
            {"user_id": save["user_id"], "deleted_at": None},
            {"$set": {"deleted_at": now(), "updated_at": now()}},
        )
        return None
    migrated = _migrate_save(save)
    character = migrated["character"]
    apply_owned_grants(character, owned_packs)
    character["unlocked_paths"] = compute_paths(character, owned_packs)
    if migrated.get("alive") and not migrated.get("current_event"):
        migrated["current_event"] = fallback_event(character, migrated["history"], migrated["generation"])
    await persist_save(migrated)
    return migrated


def client_save(save: dict[str, Any]) -> dict[str, Any]:
    view = public_doc(save) or {}
    view.pop("deleted_at", None)
    return view


class SessionIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=200)
    name: str = Field(default="Player", max_length=40)


class NewGameIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    background_key: str


class ChoiceIn(BaseModel):
    choice_index: int


class HeirIn(BaseModel):
    heir_id: str
    name: str | None = None


class BuyIn(BaseModel):
    pack_id: str


@api.get("/health")
async def health() -> dict[str, str]:
    store = require_db()
    return {"ok": "true", "db": store.kind}


@api.post("/auth/session")
async def auth_session(body: SessionIn) -> dict[str, Any]:
    store = require_db()
    used = await store.exchanges.find_one({"session_id": body.session_id})
    if used:
        raise HTTPException(status_code=401, detail="Session already used")
    user = {
        "user_id": str(uuid.uuid4()),
        "name": clean_name(body.name, "Player"),
        "email": "",
        "deleted_at": None,
        "created_at": now(),
    }
    token = secrets.token_urlsafe(32)
    session = {
        "session_token": token,
        "user_id": user["user_id"],
        "expires_at": now() + timedelta(days=7),
        "deleted_at": None,
        "created_at": now(),
    }
    await store.users.insert_one(user)
    await store.sessions.insert_one(session)
    await store.exchanges.insert_one({"session_id": body.session_id, "user_id": user["user_id"], "created_at": now()})
    await ensure_profile(user["user_id"])
    return {"session_token": token, "user": public_doc(user)}


@api.get("/auth/me")
async def auth_me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {"user": user}


@api.post("/auth/logout")
async def auth_logout(authorization: str | None = Header(default=None), user: dict[str, Any] = Depends(current_user)) -> dict[str, bool]:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    store = require_db()
    await store.sessions.update_one(
        {"session_token": token, "user_id": user["user_id"]},
        {"$set": {"deleted_at": now()}},
    )
    return {"ok": True}


@api.get("/game/backgrounds")
async def game_backgrounds() -> dict[str, Any]:
    items = [
        {"key": key, "label": value["label"], "blurb": value["blurb"]}
        for key, value in BACKGROUNDS.items()
    ]
    return {"backgrounds": items}


@api.get("/game/state")
async def game_state(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = await ensure_profile(user["user_id"])
    save = await load_active_save(user["user_id"])
    if not save:
        return {"save": None}
    repaired = await repair_save(save, list(profile.get("owned_packs") or []))
    return {"save": client_save(repaired) if repaired else None}


@api.post("/game/new")
async def game_new(body: NewGameIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if body.background_key not in BACKGROUNDS:
        raise HTTPException(status_code=400, detail="Unknown background")
    existing = await load_active_save(user["user_id"])
    if existing:
        raise HTTPException(status_code=409, detail="A record is already open. Choose an heir or abandon it.")
    profile = await ensure_profile(user["user_id"])
    owned = list(profile.get("owned_packs") or [])
    character = fresh_character(body.name, body.background_key, owned)
    opening = await generate_event(character, [], owned, 1)
    save = {
        "user_id": user["user_id"],
        "generation": 1,
        "alive": True,
        "cause_of_death": None,
        "character": character,
        "current_event": opening,
        "last_outcome": None,
        "history": [],
        "lineage": [],
        "marks_earned": 0,
        "deleted_at": None,
        "created_at": now(),
        "updated_at": now(),
    }
    store = require_db()
    await store.saves.insert_one(save)
    return {"save": client_save(save)}


async def finish_death(save: dict[str, Any], cause: str) -> dict[str, Any]:
    profile = await ensure_profile(save["user_id"])
    if save.get("alive"):
        earned = marks_for_life(save["character"], int(save["generation"]))
        save["alive"] = False
        save["cause_of_death"] = cause[:180]
        save["marks_earned"] = earned
        profile["marks"] = int(profile["marks"]) + earned
        profile["lives_lived"] = int(profile["lives_lived"]) + 1
        store = require_db()
        await store.profiles.update_one(
            {"user_id": save["user_id"], "deleted_at": None},
            {"$set": {"marks": profile["marks"], "lives_lived": profile["lives_lived"], "updated_at": now()}},
        )
    return profile


@api.post("/game/choice")
async def game_choice(body: ChoiceIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = await ensure_profile(user["user_id"])
    save = await load_active_save(user["user_id"])
    if not save:
        raise HTTPException(status_code=404, detail="No life is open")
    owned = list(profile.get("owned_packs") or [])
    save = await repair_save(save, owned)
    if not save or not save.get("alive"):
        raise HTTPException(status_code=409, detail="This life is already over")
    event_now = save.get("current_event") or {}
    choices = event_now.get("choices") or []
    if body.choice_index < 0 or body.choice_index >= len(choices):
        raise HTTPException(status_code=400, detail="That choice is not on the page")
    picked = choices[body.choice_index]
    character = save["character"]
    age_now = int(character["age_years"])
    apply_choice(character, picked)
    line = f"Age {age_now}: {event_now.get('title')} — {picked.get('label')}."
    character["life_log"].append(line)
    if picked.get("milestone"):
        character["life_log"].append(str(picked["milestone"])[:180])
    trim_log(character["life_log"])
    save["history"].append(
        {
            "age": age_now,
            "title": event_now.get("title"),
            "choice": picked.get("label"),
            "outcome": picked.get("outcome"),
        }
    )
    trim_log(save["history"])
    save["last_outcome"] = picked.get("outcome")
    died = bool(picked.get("fatal")) or int(character["stats"]["health"]) <= 0
    if died:
        cause = str(picked.get("outcome") or "The body gave out.")
        if int(character["stats"]["health"]) <= 0 and not picked.get("fatal"):
            cause = str(picked.get("outcome") or "Health failed.")
        await finish_death(save, cause)
        save["current_event"] = None
    else:
        advance_life(character, owned)
        if int(character["stats"]["health"]) <= 0 or int(character["age_years"]) >= 105:
            await finish_death(save, "The body kept its own calendar.")
            save["current_event"] = None
        else:
            save["current_event"] = await generate_event(character, save["history"], owned, int(save["generation"]))
    await persist_save(save)
    fresh_profile = await ensure_profile(user["user_id"])
    return {"save": client_save(save), "profile": profile_view(fresh_profile), "marks_earned": int(save.get("marks_earned") or 0)}


@api.get("/game/heirs")
async def game_heirs(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = await ensure_profile(user["user_id"])
    save = await load_active_save(user["user_id"])
    if not save:
        raise HTTPException(status_code=404, detail="No life is open")
    save = await repair_save(save, list(profile.get("owned_packs") or []))
    if not save or save.get("alive"):
        raise HTTPException(status_code=409, detail="The life has not ended")
    character = save["character"]
    heirs = []
    for child in character.get("children") or []:
        age_now = max(0, int(character["age_years"]) - int(child.get("born_parent_age") or 0))
        heirs.append({"id": child["id"], "name": child["name"], "age_now": age_now, "kind": "child"})
    heirs.append({"id": "new", "name": "A distant relative", "age_now": 0, "kind": "new"})
    return {
        "obituary": obituary(save),
        "marks_earned": int(save.get("marks_earned") or 0),
        "marks_balance": int(profile["marks"]),
        "heirs": heirs,
    }


@api.post("/game/heir")
async def game_heir(body: HeirIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = await ensure_profile(user["user_id"])
    owned = list(profile.get("owned_packs") or [])
    save = await load_active_save(user["user_id"])
    if not save:
        raise HTTPException(status_code=404, detail="No life is open")
    save = await repair_save(save, owned)
    if not save or save.get("alive"):
        raise HTTPException(status_code=409, detail="Choose an heir only after a death")
    parent = save["character"]
    chosen = None
    if body.heir_id != "new":
        chosen = next((child for child in parent.get("children") or [] if child.get("id") == body.heir_id), None)
        if not chosen:
            raise HTTPException(status_code=404, detail="That child is not in the line")
    nxt = heir_character(parent, chosen, body.name)
    apply_owned_grants(nxt, owned)
    nxt["unlocked_paths"] = compute_paths(nxt, owned)
    heir_name = nxt["name"]
    save["lineage"].append(epitaph(save, body.heir_id, heir_name))
    trim_log(save["lineage"], 40)
    save["generation"] = int(save["generation"]) + 1
    save["alive"] = True
    save["cause_of_death"] = None
    save["character"] = nxt
    save["history"] = []
    save["last_outcome"] = None
    save["marks_earned"] = 0
    save["current_event"] = await generate_event(nxt, [], owned, int(save["generation"]))
    await persist_save(save)
    return {"save": client_save(save)}


@api.post("/game/abandon")
async def game_abandon(user: dict[str, Any] = Depends(current_user)) -> dict[str, bool]:
    save = await load_active_save(user["user_id"])
    if not save:
        return {"ok": True}
    store = require_db()
    await store.saves.update_one(
        {"user_id": user["user_id"], "deleted_at": None},
        {"$set": {"deleted_at": now(), "updated_at": now()}},
    )
    return {"ok": True}


@api.get("/profile")
async def get_profile(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = await ensure_profile(user["user_id"])
    return {"profile": profile_view(profile)}


@api.get("/store")
async def get_store(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = await ensure_profile(user["user_id"])
    owned = set(profile.get("owned_packs") or [])
    packs = []
    for pack in STORE_PACKS:
        packs.append(
            {
                "id": pack["id"],
                "category": pack["category"],
                "name": pack["name"],
                "blurb": pack["blurb"],
                "cost": pack["cost"],
                "owned": pack["id"] in owned,
            }
        )
    return {"marks": int(profile["marks"]), "lives_lived": int(profile["lives_lived"]), "categories": list(CATEGORIES), "packs": packs}


@api.post("/store/buy")
async def store_buy(body: BuyIn, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    pack = PACKS_BY_ID.get(body.pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Unknown pack")
    profile = await ensure_profile(user["user_id"])
    if body.pack_id in (profile.get("owned_packs") or []):
        raise HTTPException(status_code=409, detail="You already keep this")
    if int(profile["marks"]) < int(pack["cost"]):
        raise HTTPException(status_code=402, detail="Not enough Legacy Marks")
    store = require_db()
    result = await store.profiles.update_one(
        {"user_id": user["user_id"], "deleted_at": None, "marks": {"$gte": int(pack["cost"])}, "owned_packs": {"$ne": body.pack_id}},
        {"$inc": {"marks": -int(pack["cost"])}, "$addToSet": {"owned_packs": body.pack_id}, "$set": {"updated_at": now()}},
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=409, detail="The purchase did not land")
    updated = await ensure_profile(user["user_id"])
    save = await load_active_save(user["user_id"])
    if save and save.get("alive") and isinstance(save.get("character"), dict):
        owned = list(updated.get("owned_packs") or [])
        repaired = await repair_save(save, owned)
        if repaired:
            await persist_save(repaired)
    return {"profile": profile_view(updated), "pack_id": body.pack_id}


app.include_router(api)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)
