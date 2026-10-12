import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException

import server
from server import CHECKOUT_NOT_CONFIGURED


async def open_session(client, session_id: str, name: str = "Ada"):
    response = await client.post("/api/auth/session", json={"session_id": session_id, "name": name})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['session_token']}"}, body["user"]["user_id"]


def _sign(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _event(event_id: str, session_id: str, user_id: str, *, paid: bool = True, kind: str = "checkout.session.completed") -> bytes:
    body = {
        "id": event_id,
        "object": "event",
        "type": kind,
        "livemode": False,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "mode": "payment",
                "payment_status": "paid" if paid else "unpaid",
                "metadata": {
                    "user_id": user_id,
                    "pack_id": "coins100",
                    "coins": "999999",
                    "platform": "ios",
                },
            }
        },
    }
    return json.dumps(body, separators=(",", ":")).encode()


async def _wallets(user_id: str) -> dict:
    stored = await server.db.profiles.find_one({"user_id": user_id, "deleted_at": None})
    assert stored is not None
    return stored["coins"]


async def _post_event(client, payload: bytes, secret: str, signature: str | None = None):
    return await client.post(
        "/api/store/stripe-webhook",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": signature if signature is not None else _sign(payload, secret),
        },
    )


async def test_flat_coins_migrate_into_the_web_wallet_once(client):
    headers, user_id = await open_session(client, "session-wallet-migrate")
    for doc in server.db.profiles.docs:
        if doc.get("user_id") == user_id:
            doc["coins"] = 80
    web = await client.get("/api/profile", headers={**headers, "X-Legacy-Platform": "web"})
    ios = await client.get("/api/profile", headers={**headers, "X-Legacy-Platform": "ios"})
    assert web.json()["profile"]["coins"] == 80
    assert ios.json()["profile"]["coins"] == 0
    assert "_id" not in web.json()["profile"]
    stored = await _wallets(user_id)
    assert stored == {"web": 80, "ios": 0, "android": 0}
    again = await client.get("/api/profile", headers={**headers, "X-Legacy-Platform": "web"})
    assert again.json()["profile"]["coins"] == 80
    assert await _wallets(user_id) == {"web": 80, "ios": 0, "android": 0}


async def test_store_buy_deducts_only_the_request_platform(client):
    headers, user_id = await open_session(client, "session-wallet-deduct")
    for doc in server.db.profiles.docs:
        if doc.get("user_id") == user_id:
            doc["coins"] = {"web": 10000, "ios": 10, "android": 4}
            doc["marks"] = 250
    short = await client.post(
        "/api/store/buy",
        headers={**headers, "X-Legacy-Platform": "ios"},
        json={"pack_id": "supernatural-vampire", "platform": "web"},
    )
    assert short.status_code == 402
    assert short.json()["detail"] == "Not enough Coins"
    assert await _wallets(user_id) == {"web": 10000, "ios": 10, "android": 4}
    stored = await server.db.profiles.find_one({"user_id": user_id, "deleted_at": None})
    assert "supernatural-vampire" not in (stored.get("owned_packs") or [])
    assert "coins.ios" not in stored
    bought = await client.post(
        "/api/store/buy",
        headers={**headers, "X-Legacy-Platform": "web"},
        json={"pack_id": "supernatural-vampire"},
    )
    assert bought.status_code == 200, bought.text
    assert bought.json()["profile"]["coins"] == 7500
    assert bought.json()["profile"]["marks"] == 250
    assert await _wallets(user_id) == {"web": 7500, "ios": 10, "android": 4}


async def test_checkout_returns_a_url_without_secrets(client, monkeypatch):
    headers, user_id = await open_session(client, "session-web-checkout")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example_not_a_real_key")
    seen: dict = {}

    def fake_open(params):
        seen.update(params)
        assert "payment_method_types" not in params
        return "https://checkout.stripe.com/c/pay/cs_test_example"

    monkeypatch.setattr(server, "open_stripe_checkout", fake_open)
    response = await client.post(
        "/api/store/web-checkout",
        headers={**headers, "Origin": "http://localhost:3010", "X-Legacy-Platform": "ios"},
        json={"pack_id": "coins100", "platform": "ios"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"url": "https://checkout.stripe.com/c/pay/cs_test_example"}
    assert "sk_" not in response.text
    assert "whsec_" not in response.text
    assert seen["mode"] == "payment"
    assert seen["metadata"]["user_id"] == user_id
    assert seen["metadata"]["pack_id"] == "coins100"
    assert seen["metadata"]["coins"] == "100"
    assert "platform" not in seen["metadata"]
    assert seen["line_items"][0]["price_data"]["unit_amount"] == 99
    assert seen["success_url"].startswith("http://localhost:3010/store?checkout=success")
    assert seen["integration_identifier"].startswith("legacy_web_coins_")
    assert len(seen["integration_identifier"].rsplit("_", 1)[-1]) == 8


async def test_checkout_without_a_test_key_is_a_configuration_error(client, monkeypatch):
    headers, _user_id = await open_session(client, "session-web-checkout-off")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    missing = await client.post(
        "/api/store/web-checkout",
        headers={**headers, "Origin": "http://127.0.0.1:3011"},
        json={"pack_id": "coins250"},
    )
    assert missing.status_code == 503
    assert missing.json()["detail"] == CHECKOUT_NOT_CONFIGURED
    assert "sk_" not in missing.text
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_must_not_charge")
    live = await client.post(
        "/api/store/web-checkout",
        headers={**headers, "Origin": "http://127.0.0.1:3011"},
        json={"pack_id": "coins250"},
    )
    assert live.status_code == 503
    assert "sk_live_" not in live.text
    assert "must_not_charge" not in live.text


def test_verifier_rejects_a_bad_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_unit_test_secret")
    with pytest.raises(HTTPException) as caught:
        server.verify_stripe_event(b"{}", "t=1,v1=deadbeef")
    assert caught.value.status_code == 400
    assert "whsec_" not in str(caught.value.detail)


async def test_webhook_grants_the_web_wallet_once(client, monkeypatch):
    headers, user_id = await open_session(client, "session-webhook-grant")
    for doc in server.db.profiles.docs:
        if doc.get("user_id") == user_id:
            doc["coins"] = {"web": 5, "ios": 9, "android": 7}
    secret = "whsec_unit_test_secret"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_should_not_appear")
    payload = _event("evt_paid_1", "cs_test_1", user_id)
    unpaid = _event("evt_unpaid_1", "cs_test_unpaid", user_id, paid=False)
    refused = await _post_event(client, unpaid, secret)
    assert refused.status_code == 200
    assert await _wallets(user_id) == {"web": 5, "ios": 9, "android": 7}
    bad = await _post_event(client, payload, secret, signature="t=1,v1=nope")
    assert bad.status_code == 400
    assert "whsec_" not in bad.text
    assert "sk_test_" not in bad.text
    assert await _wallets(user_id) == {"web": 5, "ios": 9, "android": 7}
    granted = await _post_event(client, payload, secret)
    assert granted.status_code == 200, granted.text
    assert granted.json() == {"received": True}
    assert "_id" not in granted.json()
    assert "sk_" not in granted.text
    assert await _wallets(user_id) == {"web": 105, "ios": 9, "android": 7}
    again = await _post_event(client, payload, secret)
    assert again.status_code == 200
    assert await _wallets(user_id) == {"web": 105, "ios": 9, "android": 7}
    other = _event(
        "evt_paid_2",
        "cs_test_1",
        user_id,
        kind="checkout.session.async_payment_succeeded",
    )
    duplicate_session = await _post_event(client, other, secret)
    assert duplicate_session.status_code == 200
    assert await _wallets(user_id) == {"web": 105, "ios": 9, "android": 7}
