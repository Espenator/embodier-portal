"""Member-facing API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..auth import verify_session_token
from ..config import settings
from ..db import get_db
from ..deps import get_current_member, require_brain_secret
from ..models import Document, Holding, Interest, Member
from ..presentation import TIERS, present, voice_for

router = APIRouter(prefix="/api")


class VerifyIn(BaseModel):
    token: str


class InterestIn(BaseModel):
    offering_id: str
    note: str = ""


class ProvisionIn(BaseModel):
    phone: str
    tier: str = "inner_circle"
    display_name: str = ""
    is_broker: bool = False


EXCHANGE_STATUS = {
    # pre-DASP: nothing trades. Every trading-adjacent response carries this.
    "status": "waitlist_only",
    "message": ("Trading is not live yet. The exchange opens to the waitlist "
                "first — your place is held."),
}


def _member_shape(m: Member) -> dict:
    return {
        "phone": m.phone,
        "tier": m.tier,
        "status": m.status,
        "is_broker": m.is_broker,
        "display_name": m.display_name,
        "greeting": present(m.tier, "greeting"),
    }


@router.post("/session/verify")
def session_verify(body: VerifyIn, db: DBSession = Depends(get_db)):
    """Validate a Brain-issued session token. Returns the member when the
    token is genuine and unexpired; 401 otherwise."""
    parsed = verify_session_token(body.token, settings.BRAIN_SHARED_SECRET)
    if not parsed:
        raise HTTPException(status_code=401,
                            detail="invalid or expired session")
    phone, _exp = parsed
    member = db.get(Member, phone)
    if member is None or member.status != "active":
        raise HTTPException(status_code=401,
                            detail="member not found or inactive")
    return {"ok": True, "member": _member_shape(member)}


@router.post("/internal/members")
def provision_member(body: ProvisionIn, _s=Depends(require_brain_secret),
                     db: DBSession = Depends(get_db)):
    """Brain-only: create (or refresh) a member after OTP verification."""
    if body.tier not in TIERS:
        raise HTTPException(status_code=400, detail="unknown tier")
    member = db.get(Member, body.phone)
    if member is None:
        member = Member(phone=body.phone, tier=body.tier,
                        display_name=body.display_name[:120],
                        is_broker=bool(body.is_broker))
        db.add(member)
    else:
        member.tier = body.tier
        if body.display_name:
            member.display_name = body.display_name[:120]
        member.is_broker = bool(body.is_broker)
        member.status = "active"
    db.commit()
    return {"ok": True, "member": _member_shape(member)}


@router.get("/me")
def me(member: Member = Depends(get_current_member)):
    return {"member": _member_shape(member),
            "voice": voice_for(member.tier)}


@router.get("/portfolio")
def portfolio(member: Member = Depends(get_current_member),
              db: DBSession = Depends(get_db)):
    rows = (db.query(Holding).filter_by(phone=member.phone)
            .order_by(Holding.created_at.desc()).all())
    holdings = [{
        "id": h.id, "asset_name": h.asset_name, "asset_kind": h.asset_kind,
        "amount": float(h.amount), "currency": h.currency,
        "status": h.status,
    } for h in rows]
    return {
        "title": present(member.tier, "portfolio_title"),
        "empty_note": present(member.tier, "portfolio_empty"),
        "holdings": holdings,
        "exchange": EXCHANGE_STATUS,
    }


@router.get("/interests")
def list_interests(member: Member = Depends(get_current_member),
                   db: DBSession = Depends(get_db)):
    rows = (db.query(Interest).filter_by(phone=member.phone)
            .order_by(Interest.created_at.desc()).all())
    return {
        "title": present(member.tier, "interests_title"),
        "cta": present(member.tier, "interests_cta"),
        "interests": [{
            "id": r.id, "offering_id": r.offering_id, "note": r.note,
            "status": r.status,
        } for r in rows],
    }


@router.post("/interests")
def express_interest(body: InterestIn,
                     member: Member = Depends(get_current_member),
                     db: DBSession = Depends(get_db)):
    """Express interest in an offering. Pre-DASP this only waitlists —
    it is never a purchase or allocation."""
    if not body.offering_id.strip():
        raise HTTPException(status_code=400, detail="offering_id required")
    row = Interest(phone=member.phone,
                   offering_id=body.offering_id.strip()[:120],
                   note=body.note[:500], status="waitlisted")
    db.add(row)
    db.commit()
    return {
        "ok": True,
        "interest": {"id": row.id, "offering_id": row.offering_id,
                     "status": row.status},
        "note": ("Your place is held on the waitlist. This is not a "
                 "purchase — a $100 fully refundable deposit is collected "
                 "only when projects are offered."),
    }


@router.get("/documents")
def documents(member: Member = Depends(get_current_member),
              db: DBSession = Depends(get_db)):
    rows = (db.query(Document).filter_by(phone=member.phone)
            .order_by(Document.created_at.desc()).all())
    return {
        "title": present(member.tier, "documents_title"),
        "documents": [{
            "id": d.id, "title": d.title, "doc_type": d.doc_type,
            "url": d.url,
        } for d in rows],
    }
