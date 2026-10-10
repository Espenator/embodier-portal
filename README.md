# Embodier Portal

The member-facing portal for Embodier.ai — the signed-in home every member
opens after phone+OTP signup on the Brain (WhatsApp/SMS). The frontend renders
tier-personalized panels (Inner Circle / Equity Plus / Capital Partner /
institution); the backend API serves profile, portfolio, interests, documents,
and broker panels.

## Repo layout

| Path | What it is |
|---|---|
| `index.html`, `js/` | Static frontend. Set `js/config.js` `apiBase` to the backend URL for live mode; empty = demo mode with mock content. |
| `assets/` | Portal imagery. |
| `backend/` | FastAPI accounts API (Python 3.12). See `backend/README.md`. |

## Run the backend (local)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# env (never commit secrets)
export DATABASE_URL=<redacted>   # dev: sqlite auto-creates on boot
export BRAIN_SHARED_SECRET=<redacted>

# prod: apply versioned migrations first
DATABASE_URL=<redacted> .venv/bin/python migrations/migrate.py

.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Tests: `cd backend && .venv/bin/python -m pytest tests/` (22 tests, sqlite).

## Wire the frontend to the backend

1. Deploy the backend (see the portal deploy kit in
   `~/workspace/parallel-build/wave3/portal-deploy/` on the build box, or
   `backend/Dockerfile`).
2. Copy `js/config.example.js` to `js/config.js` and set `apiBase` to the
   backend URL (no trailing slash). The backend must allow this origin via CORS.
3. Set `loginUrl` to the Brain's phone+OTP login page. After login, the Brain
   hands the portal an HMAC session token (`js/session.js`).

## Auth

Passwordless only: phone + 6-digit OTP on the Brain, which mints HMAC session
tokens this API verifies. No passwords, no Google sign-in — ever.
