"""Brain session-token scheme.

Token format:  base64url(phone) + "." + exp_epoch + "." + hex_hmac

    sig = HMAC-SHA256(BRAIN_SHARED_SECRET, "<phone_b64>.<exp>")

The Brain mints tokens after a successful phone+OTP verification; this API
only *verifies* them (never mints, never sees OTPs or passwords — there are
none). Verification is constant-time and checks expiry.

Brain-side minting (Python):

    import base64, hashlib, hmac, time
    def mint_session_token(phone: str, secret: str, ttl_s: int = 2592000) -> str:
        exp = str(int(time.time()) + ttl_s)
        body = base64.urlsafe_b64encode(phone.encode()).decode().rstrip("=") \\
            + "." + exp
        sig = hmac.new(secret.encode(), body.encode(),
                       hashlib.sha256).hexdigest()
        return body + "." + sig
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_session_token(phone: str, secret: str, ttl_s: int = 2592000,
                       now: int | None = None) -> str:
    """Mint a token. Used by tests and documented for the Brain; the API
    itself never mints."""
    exp = str(int(now if now is not None else time.time()) + ttl_s)
    body = _b64e(phone.encode()) + "." + exp
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + sig


def verify_session_token(token: str, secret: str,
                         now: int | None = None) -> tuple[str, int] | None:
    """Return (phone, exp) if valid, else None."""
    if not secret or not token:
        return None
    try:
        body, sig = token.rsplit(".", 1)
        phone_b64, exp_s = body.split(".", 1)
        exp = int(exp_s)
    except (ValueError, AttributeError):
        return None
    want = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, sig):
        return None
    if exp <= int(now if now is not None else time.time()):
        return None
    try:
        phone = _b64d(phone_b64).decode()
    except Exception:
        return None
    if not phone or len(phone) > 32:
        return None
    return phone, exp


def token_fingerprint(token: str) -> str:
    """Stable, non-reversible handle for session bookkeeping."""
    return hashlib.sha256(token.encode()).hexdigest()
