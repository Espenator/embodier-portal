# Embodier Portal — Accounts API (backend)

Member + broker panel backend for Embodier.ai. Members authenticate
passwordless (phone + OTP on the Brain); this API trusts Brain-issued
session tokens and serves profile, portfolio, interests, documents, and
the broker panel. Standalone service — replaces the Apps Script prototype.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# env (never commit secrets)
export DATABASE_URL="sqlite:///./portal.db"          # dev
# export DATABASE_URL="postgresql+psycopg://user:pass@host/db"  # prod
export BRAIN_SHARED_SECRET="..."                     # shared with the Brain

# prod: apply versioned migrations first
DATABASE_URL="postgresql+psycopg://user:pass@host/db" \
  .venv/bin/python migrations/migrate.py

# dev: tables auto-create on boot
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health: `GET /healthz`.

## Auth — Brain session tokens

The Brain mints tokens after OTP verification; this API only verifies.

Token format: `base64url(phone) + "." + exp_epoch + "." + hex_hmac`

```
sig = HMAC-SHA256(BRAIN_SHARED_SECRET, "<phone_b64>.<exp>")
```

Mint (Python, Brain side):

```python
import base64, hashlib, hmac, time
def mint_session_token(phone, secret, ttl_s=2592000):
    exp = str(int(time.time()) + ttl_s)
    body = base64.urlsafe_b64encode(phone.encode()).decode().rstrip("=") + "." + exp
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + sig
```

Clients send `Authorization: Bearer <token>`. The API also exposes
`POST /api/session/verify` (`{"token": ...}` → member or 401) for
frontends that verify once and hold the session.

Brain-only provisioning: `POST /api/internal/members`
(`{"phone","tier","display_name","is_broker"}`) requires header
`X-Brain-Secret: <BRAIN_SHARED_SECRET>`. The Brain calls this right after
OTP verification so the member exists before first login.

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | /healthz | — | liveness |
| POST | /api/session/verify | — | body `{"token"}` → member or 401 |
| POST | /api/internal/members | brain secret | create/refresh member |
| GET | /api/me | bearer | profile + tier voice block |
| GET | /api/portfolio | bearer | holdings + `exchange: waitlist_only` |
| GET | /api/interests | bearer | member's interests |
| POST | /api/interests | bearer | express interest → status `waitlisted` |
| GET | /api/documents | bearer | member's documents |
| GET | /api/broker/deals | bearer+broker | broker's deals |
| GET | /api/broker/pipeline | bearer+broker | stage counts + deals per stage |
| GET | /api/broker/commissions | bearer+broker | commission status + expected amounts |
| GET | /api/broker/buybox | bearer+broker | buy-box criteria |

## Tier personalization

`app/presentation.py` is the presentation layer: every member response
carries copy/posture for the member's tier (`inner_circle` = warm community
voice, `equity_plus` = ownership voice, `capital_partner` = institutional
voice). Endpoints call `present(tier, key)` — no tier strings hardcoded in
routers. Unknown tiers fall back to the Inner Circle voice.

## Compliance (pre-DASP)

- No trading, no token sales: `GET /api/portfolio` always includes
  `"exchange": {"status": "waitlist_only", ...}`.
- `POST /api/interests` only ever creates `waitlisted` interests and
  states plainly that it is not a purchase; the $100 refundable deposit
  is collected only when projects are offered.
- No yield promises, no fee figures, no live-sale claims anywhere.

## Tiers

`inner_circle` ($500+), `equity_plus` ($5,000+), `capital_partner` ($50,000+).

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

22 tests, sqlite in-memory (no Postgres needed). Postgres behavior is
covered by `migrations/*.sql`, which are plain Postgres DDL.

## Docker

```bash
docker build -t portal-api .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://user:pass@host/db" \
  -e BRAIN_SHARED_SECRET="..." portal-api
```
