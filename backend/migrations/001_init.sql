-- 001_init.sql — core member portal schema (Postgres)
CREATE TABLE IF NOT EXISTS members (
    phone        TEXT PRIMARY KEY,
    tier         TEXT NOT NULL DEFAULT 'inner_circle'
                 CHECK (tier IN ('inner_circle','equity_plus','capital_partner')),
    status       TEXT NOT NULL DEFAULT 'active',
    is_broker    BOOLEAN NOT NULL DEFAULT FALSE,
    display_name TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id         SERIAL PRIMARY KEY,
    phone      TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sessions_phone ON sessions(phone);

CREATE TABLE IF NOT EXISTS holdings (
    id         SERIAL PRIMARY KEY,
    phone      TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    asset_name TEXT NOT NULL,
    asset_kind TEXT NOT NULL DEFAULT 'embodiment',
    amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
    currency   TEXT NOT NULL DEFAULT 'USD',
    status     TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_holdings_phone ON holdings(phone);

CREATE TABLE IF NOT EXISTS interests (
    id          SERIAL PRIMARY KEY,
    phone       TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    offering_id TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    -- pre-DASP: every interest lands waitlisted; never a purchase.
    status      TEXT NOT NULL DEFAULT 'waitlisted',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_interests_phone ON interests(phone);

CREATE TABLE IF NOT EXISTS documents (
    id         SERIAL PRIMARY KEY,
    phone      TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    doc_type   TEXT NOT NULL DEFAULT 'general',
    url        TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_documents_phone ON documents(phone);
