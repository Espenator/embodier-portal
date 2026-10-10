#!/usr/bin/env python3
"""Minimal migration runner. Applies migrations/*.sql in filename order.

Tracks applied files in schema_migrations(filename). Requires psycopg for
Postgres. Usage:

    DATABASE_URL=postgresql+psycopg://user:pass@host/db python3 migrations/migrate.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MIGRATIONS = Path(__file__).parent


def main() -> int:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        print("migrate.py targets Postgres; set DATABASE_URL "
              "to a postgresql+psycopg:// URL", file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("psycopg is required: pip install 'psycopg[binary]'",
              file=sys.stderr)
        return 2

    files = sorted(p.name for p in MIGRATIONS.glob("*.sql"))
    with psycopg.connect(url.replace("postgresql+psycopg://",
                                      "postgresql://")) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                        "(filename TEXT PRIMARY KEY, applied_at "
                        "TIMESTAMPTZ NOT NULL DEFAULT now())")
            cur.execute("SELECT filename FROM schema_migrations")
            done = {r[0] for r in cur.fetchall()}
            for f in files:
                if f in done:
                    print(f"skip {f}")
                    continue
                sql = (MIGRATIONS / f).read_text()
                cur.execute(sql)
                cur.execute("INSERT INTO schema_migrations(filename) "
                            "VALUES (%s)", (f,))
                print(f"applied {f}")
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
