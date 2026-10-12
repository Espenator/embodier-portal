-- 003_course.sql — $100 Investment Real Estate Course (Postgres)
--
-- Enrollments are created by the Brain's Stripe webhook via
-- POST /api/internal/course/enroll (keyed by verified phone).
-- Quiz grading is server-side; answer keys live in course/content/*.json
-- and are never served to clients.

CREATE TABLE IF NOT EXISTS course_enrollments (
    phone       TEXT PRIMARY KEY REFERENCES members(phone) ON DELETE CASCADE,
    source      TEXT NOT NULL DEFAULT 'stripe',
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS course_module_progress (
    id           SERIAL PRIMARY KEY,
    phone        TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    module_id    TEXT NOT NULL,
    lessons_done INTEGER NOT NULL DEFAULT 0,
    quiz_passed  BOOLEAN NOT NULL DEFAULT FALSE,
    quiz_best    INTEGER NOT NULL DEFAULT 0,
    quiz_attempts INTEGER NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (phone, module_id)
);
CREATE INDEX IF NOT EXISTS ix_course_module_progress_phone
    ON course_module_progress(phone);

CREATE TABLE IF NOT EXISTS course_quiz_attempts (
    id         SERIAL PRIMARY KEY,
    phone      TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    module_id  TEXT NOT NULL,
    score      INTEGER NOT NULL,
    total      INTEGER NOT NULL,
    passed     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_course_quiz_attempts_phone
    ON course_quiz_attempts(phone);

CREATE TABLE IF NOT EXISTS course_certificates (
    phone          TEXT PRIMARY KEY REFERENCES members(phone) ON DELETE CASCADE,
    certificate_id TEXT NOT NULL UNIQUE,
    certified_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS referral_codes (
    code       TEXT PRIMARY KEY,
    phone      TEXT NOT NULL UNIQUE REFERENCES members(phone) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_referral_codes_phone ON referral_codes(phone);

CREATE TABLE IF NOT EXISTS referral_events (
    id             SERIAL PRIMARY KEY,
    referrer_phone TEXT NOT NULL REFERENCES members(phone) ON DELETE CASCADE,
    referred_phone TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (referred_phone)
);
CREATE INDEX IF NOT EXISTS ix_referral_events_referrer
    ON referral_events(referrer_phone);
