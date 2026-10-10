-- 002_broker.sql — broker panel tables (Postgres)
CREATE TABLE IF NOT EXISTS broker_deals (
    id                SERIAL PRIMARY KEY,
    broker_phone      TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    property_name     TEXT NOT NULL,
    stage             TEXT NOT NULL DEFAULT 'sourced'
                      CHECK (stage IN ('sourced','contacted','evaluating',
                                       'offer','under_contract','closed','paid')),
    deal_value        NUMERIC(18,2),
    commission_pct    NUMERIC(6,3),
    commission_status TEXT NOT NULL DEFAULT 'pending',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_broker_deals_phone ON broker_deals(broker_phone);

CREATE TABLE IF NOT EXISTS broker_buybox (
    id           SERIAL PRIMARY KEY,
    broker_phone TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    region       TEXT NOT NULL DEFAULT '',
    min_keys     INTEGER,
    max_keys     INTEGER,
    notes        TEXT NOT NULL DEFAULT '',
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_broker_buybox_phone ON broker_buybox(broker_phone);
