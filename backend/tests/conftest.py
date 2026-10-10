"""Test fixtures: sqlite in-memory DB, TestClient, minted tokens."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, config
from app.db import get_db
from app.main import create_app
from app.models import (Base, BrokerBuyBox, BrokerDeal, Document, Holding,
                        Interest, Member)

TEST_SECRET = "test-brain-secret-xyz"


@pytest.fixture()
def db():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = maker()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    config.settings.BRAIN_SHARED_SECRET = TEST_SECRET
    app = create_app()

    def _get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def seed_member(db, phone="+15550001111", tier="inner_circle",
                is_broker=False, status="active", name="Test Member"):
    m = Member(phone=phone, tier=tier, status=status, is_broker=is_broker,
               display_name=name)
    db.add(m)
    db.commit()
    return m


def bearer(phone, secret=TEST_SECRET, ttl_s=3600):
    return {"Authorization": "Bearer " + auth.mint_session_token(
        phone, secret, ttl_s=ttl_s)}


@pytest.fixture()
def member(db):
    return seed_member(db)


@pytest.fixture()
def broker_member(db):
    return seed_member(db, phone="+15550002222", tier="capital_partner",
                       is_broker=True, name="Broker Bob")


@pytest.fixture()
def seeded(db, member, broker_member):
    db.add(Holding(phone=member.phone, asset_name="Casa Azul Embodiment",
                   amount=500, status="active"))
    db.add(Interest(phone=member.phone, offering_id="off-001",
                    note="loved the film", status="waitlisted"))
    db.add(Document(phone=member.phone, title="Welcome pack",
                    doc_type="onboarding", url="https://x.test/welcome.pdf"))
    db.add(BrokerDeal(
        broker_phone=broker_member.phone, property_name="Casa Miramar",
        stage="evaluating", deal_value=2500000, commission_pct=3.0,
        commission_status="pending"))
    db.add(BrokerDeal(broker_phone=broker_member.phone,
                      property_name="Villa Serena", stage="offer",
                      deal_value=1800000, commission_pct=2.5,
                      commission_status="approved"))
    db.add(BrokerBuyBox(broker_phone=broker_member.phone, region="Tulum",
                        min_keys=10, max_keys=40,
                        notes="boutique, beachfront"))
    db.commit()
    return member
