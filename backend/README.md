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
| GET | /api/course/status | bearer | enrollment + per-module progress + certified flag |
| GET | /api/course/modules | bearer | course manifest + module states (no answer keys) |
| GET | /api/course/modules/{id} | bearer | lessons + quiz questions/options (no answer keys) |
| POST | /api/course/lessons | bearer | body `{"module_id","lessons_done"}` → reading progress |
| POST | /api/course/quiz | bearer | body `{"module_id","answers[]"}` → server-graded, pass = 4/5 |
| GET | /api/course/certificate | bearer | 404 until all modules passed → `{certificate_id, certified_at}` |
| GET | /api/course/referrals | bearer | `{referral_code, signups, referred[]}` + program terms |
| POST | /api/internal/course/enroll | brain secret | enroll after Stripe webhook (verified phone). Idempotent |
| POST | /api/internal/course/referral | brain secret | attribute a signup to a referrer code. Idempotent |

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
- Course: all copy is education-framed ("learn how the pros invest").
  Quiz grading is server-side; answer keys never leave the API. The
  referral reward (5% of referred buyers' token purchases, forever) is
  stated factually with the pre-DASP note that no token sale is live.

## Course content

`course/content/` holds the course manifest (`course.json`) plus one JSON
per module with EN+ES lessons and 5-question quizzes. The API serves a
sanitized view (no answer keys); grading happens in
`POST /api/course/quiz`. The Docker image bundles `course/` (build from
the repo root: `docker build -t portal-api -f backend/Dockerfile .`).

## Tiers

`inner_circle` ($500+), `equity_plus` ($5,000+), `capital_partner` ($50,000+).

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

49 tests, sqlite in-memory (no Postgres needed). Postgres behavior is
covered by `migrations/*.sql`, which are plain Postgres DDL.

Frontend (vanilla JS, Node built-in test runner):

```bash
node --test "tests-js/**/*.test.js"
```

12 tests covering the course UI helpers, renderers, share-link builders,
and the compliance scanner over all bundled course content.

## Docker

Build from the repository root (the image bundles `course/content/`):

```bash
docker build -t portal-api -f backend/Dockerfile .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://user:pass@host/db" \
  -e BRAIN_SHARED_SECRET="..." portal-api
```
