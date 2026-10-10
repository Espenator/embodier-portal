"""Broker panel API — every endpoint requires the broker role."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from ..db import get_db
from ..deps import require_broker
from ..models import BrokerBuyBox, BrokerDeal, Member

router = APIRouter(prefix="/api/broker")

# Canonical pipeline stages, in order.
STAGES = ["sourced", "contacted", "evaluating", "offer", "under_contract",
          "closed", "paid"]


def _deal_shape(d: BrokerDeal) -> dict:
    return {
        "id": d.id,
        "property_name": d.property_name,
        "stage": d.stage,
        "deal_value": float(d.deal_value) if d.deal_value is not None else None,
        "commission_pct": (float(d.commission_pct)
                           if d.commission_pct is not None else None),
        "commission_status": d.commission_status,
    }


@router.get("/deals")
def deals(broker: Member = Depends(require_broker),
          db: DBSession = Depends(get_db)):
    rows = (db.query(BrokerDeal).filter_by(broker_phone=broker.phone)
            .order_by(BrokerDeal.updated_at.desc()).all())
    return {"deals": [_deal_shape(d) for d in rows]}


@router.get("/pipeline")
def pipeline(broker: Member = Depends(require_broker),
             db: DBSession = Depends(get_db)):
    rows = db.query(BrokerDeal).filter_by(broker_phone=broker.phone).all()
    counts = {s: 0 for s in STAGES}
    for d in rows:
        counts[d.stage] = counts.get(d.stage, 0) + 1
    by_stage = [{
        "stage": s,
        "count": counts[s],
        "deals": [_deal_shape(d) for d in rows if d.stage == s],
    } for s in STAGES]
    return {"stages": STAGES, "by_stage": by_stage,
            "total": len(rows)}


@router.get("/commissions")
def commissions(broker: Member = Depends(require_broker),
                db: DBSession = Depends(get_db)):
    rows = (db.query(BrokerDeal).filter_by(broker_phone=broker.phone).all())
    items = []
    for d in rows:
        expected = None
        if d.deal_value is not None and d.commission_pct is not None:
            expected = round(float(d.deal_value) * float(d.commission_pct)
                             / 100, 2)
        items.append({
            "deal_id": d.id,
            "property_name": d.property_name,
            "stage": d.stage,
            "commission_status": d.commission_status,
            "expected_amount": expected,
        })
    return {"commissions": items}


@router.get("/buybox")
def buybox(broker: Member = Depends(require_broker),
           db: DBSession = Depends(get_db)):
    rows = (db.query(BrokerBuyBox).filter_by(broker_phone=broker.phone)
            .order_by(BrokerBuyBox.updated_at.desc()).all())
    return {"buybox": [{
        "id": b.id, "region": b.region, "min_keys": b.min_keys,
        "max_keys": b.max_keys, "notes": b.notes,
    } for b in rows]}
