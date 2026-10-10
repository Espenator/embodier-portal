"""Auth dependencies: Bearer token -> Member; broker role gate."""
from __future__ import annotations

import datetime as dt

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from .auth import token_fingerprint, verify_session_token
from .config import settings
from .db import get_db
from .models import Member, Session


def _unauthorized(detail: str = "invalid or expired session") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                         detail=detail)


def get_current_member(authorization: str = Header(default=""),
                       db: DBSession = Depends(get_db)) -> Member:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("missing bearer token")
    parsed = verify_session_token(token.strip(), settings.BRAIN_SHARED_SECRET)
    if not parsed:
        raise _unauthorized()
    phone, exp = parsed
    member = db.get(Member, phone)
    if member is None or member.status != "active":
        raise _unauthorized("member not found or inactive")
    # bookkeeping: record/refresh the session row (best effort)
    fp = token_fingerprint(token)
    row = db.query(Session).filter_by(token_hash=fp).one_or_none()
    expires = dt.datetime.fromtimestamp(exp, dt.timezone.utc)
    if row is None:
        db.add(Session(phone=phone, token_hash=fp, expires_at=expires))
        db.commit()
    return member


def require_broker(member: Member = Depends(get_current_member)) -> Member:
    if not member.is_broker:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="broker role required")
    return member


def require_brain_secret(x_brain_secret: str = Header(default="")) -> None:
    """Internal endpoints only the Brain may call."""
    if not settings.BRAIN_SHARED_SECRET or x_brain_secret != \
            settings.BRAIN_SHARED_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="brain secret required")
