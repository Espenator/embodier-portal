"""Full API test suite — sqlite in-memory, Postgres covered by migrations/."""
from __future__ import annotations

from app import auth
from tests.conftest import TEST_SECRET, bearer, seed_member


# --- session verify -------------------------------------------------------

def test_verify_valid_token(client, member):
    token = auth.mint_session_token(member.phone, TEST_SECRET)
    r = client.post("/api/session/verify", json={"token": token})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["member"]["phone"] == member.phone
    assert body["member"]["tier"] == "inner_circle"


def test_verify_bad_signature(client, member):
    token = auth.mint_session_token(member.phone, "wrong-secret")
    r = client.post("/api/session/verify", json={"token": token})
    assert r.status_code == 401


def test_verify_expired_token(client, member):
    token = auth.mint_session_token(member.phone, TEST_SECRET, ttl_s=-10)
    r = client.post("/api/session/verify", json={"token": token})
    assert r.status_code == 401


def test_verify_unknown_member(client, db):
    token = auth.mint_session_token("+19998887777", TEST_SECRET)
    r = client.post("/api/session/verify", json={"token": token})
    assert r.status_code == 401


def test_verify_malformed_token(client):
    r = client.post("/api/session/verify", json={"token": "not.a.valid.token"})
    assert r.status_code == 401


# --- authz on protected routes --------------------------------------------

def test_me_requires_bearer(client, member):
    assert client.get("/api/me").status_code == 401
    r = client.get("/api/me", headers=bearer(member.phone))
    assert r.status_code == 200, r.text
    assert r.json()["member"]["phone"] == member.phone


def test_inactive_member_rejected(client, db):
    seed_member(db, phone="+15550009999", status="suspended")
    token = auth.mint_session_token("+15550009999", TEST_SECRET)
    r = client.get("/api/me",
                   headers={"Authorization": "Bearer " + token})
    assert r.status_code == 401


# --- member endpoints ------------------------------------------------------

def test_me_voice_varies_by_tier(client, db, member):
    seed_member(db, phone="+15550003333", tier="capital_partner")
    r1 = client.get("/api/me", headers=bearer(member.phone))
    r2 = client.get("/api/me", headers=bearer("+15550003333"))
    assert r1.json()["member"]["greeting"] != r2.json()["member"]["greeting"]
    assert "Inner Circle" in r1.json()["member"]["greeting"]
    assert "partner" in r2.json()["member"]["greeting"].lower()


def test_portfolio(client, seeded):
    r = client.get("/api/portfolio", headers=bearer(seeded.phone))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"]
    assert len(body["holdings"]) == 1
    assert body["holdings"][0]["asset_name"] == "Casa Azul Embodiment"
    # pre-DASP: no trading claims
    assert body["exchange"]["status"] == "waitlist_only"


def test_interests_roundtrip(client, member):
    r = client.post("/api/interests",
                    json={"offering_id": "off-xyz", "note": "want in"},
                    headers=bearer(member.phone))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["interest"]["status"] == "waitlisted"
    assert "not a purchase" in body["note"]

    r = client.get("/api/interests", headers=bearer(member.phone))
    ids = [i["offering_id"] for i in r.json()["interests"]]
    assert "off-xyz" in ids


def test_interests_requires_offering_id(client, member):
    r = client.post("/api/interests", json={"offering_id": "  "},
                    headers=bearer(member.phone))
    assert r.status_code == 400


def test_documents(client, seeded):
    r = client.get("/api/documents", headers=bearer(seeded.phone))
    assert r.status_code == 200, r.text
    docs = r.json()["documents"]
    assert len(docs) == 1
    assert docs[0]["title"] == "Welcome pack"


# --- brain-only provisioning ----------------------------------------------

def test_provision_requires_brain_secret(client):
    r = client.post("/api/internal/members",
                    json={"phone": "+15550004444"},
                    headers={"X-Brain-Secret": "nope"})
    assert r.status_code == 403


def test_provision_creates_member(client, db):
    r = client.post("/api/internal/members",
                    json={"phone": "+15550004444", "tier": "equity_plus",
                          "display_name": "Newbie"},
                    headers={"X-Brain-Secret": TEST_SECRET})
    assert r.status_code == 200, r.text
    assert r.json()["member"]["tier"] == "equity_plus"

    token = auth.mint_session_token("+15550004444", TEST_SECRET)
    r = client.get("/api/me", headers={"Authorization": "Bearer " + token})
    assert r.status_code == 200


def test_provision_rejects_unknown_tier(client):
    r = client.post("/api/internal/members",
                    json={"phone": "+15550005555", "tier": "platinum"},
                    headers={"X-Brain-Secret": TEST_SECRET})
    assert r.status_code == 400


# --- broker panel ----------------------------------------------------------

def test_broker_endpoints_forbid_non_brokers(client, member):
    h = bearer(member.phone)
    for path in ["/api/broker/deals", "/api/broker/pipeline",
                 "/api/broker/commissions", "/api/broker/buybox"]:
        assert client.get(path, headers=h).status_code == 403, path


def test_broker_endpoints_require_auth(client):
    assert client.get("/api/broker/deals").status_code == 401


def test_broker_deals(client, seeded, broker_member):
    r = client.get("/api/broker/deals", headers=bearer(broker_member.phone))
    assert r.status_code == 200, r.text
    deals = r.json()["deals"]
    assert len(deals) == 2
    names = {d["property_name"] for d in deals}
    assert names == {"Casa Miramar", "Villa Serena"}


def test_broker_pipeline(client, seeded, broker_member):
    r = client.get("/api/broker/pipeline",
                   headers=bearer(broker_member.phone))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    by_stage = {s["stage"]: s["count"] for s in body["by_stage"]}
    assert by_stage["evaluating"] == 1
    assert by_stage["offer"] == 1
    assert by_stage["sourced"] == 0


def test_broker_commissions(client, seeded, broker_member):
    r = client.get("/api/broker/commissions",
                   headers=bearer(broker_member.phone))
    assert r.status_code == 200, r.text
    comms = r.json()["commissions"]
    assert len(comms) == 2
    miramar = next(c for c in comms if c["property_name"] == "Casa Miramar")
    assert miramar["expected_amount"] == 75000.0  # 2.5M * 3%
    assert miramar["commission_status"] == "pending"


def test_broker_buybox(client, seeded, broker_member):
    r = client.get("/api/broker/buybox", headers=bearer(broker_member.phone))
    assert r.status_code == 200, r.text
    box = r.json()["buybox"]
    assert len(box) == 1
    assert box[0]["region"] == "Tulum"
    assert box[0]["min_keys"] == 10


def test_broker_isolation_between_brokers(client, db, seeded, broker_member):
    other = seed_member(db, phone="+15550006666", tier="equity_plus",
                        is_broker=True, name="Other Broker")
    r = client.get("/api/broker/deals", headers=bearer(other.phone))
    assert r.status_code == 200
    assert r.json()["deals"] == []
