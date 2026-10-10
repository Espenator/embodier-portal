"""Portal backend settings — everything secret comes from the environment."""
from __future__ import annotations

import os


def _req(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Settings:
    # Postgres in production, e.g. postgresql+psycopg://user:pass@host/db
    # Tests override with sqlite in-memory.
    DATABASE_URL: str = _req("DATABASE_URL", "sqlite:///./portal.db")
    # Shared secret with the Brain: it HMAC-signs session tokens, we verify.
    BRAIN_SHARED_SECRET: str = _req("BRAIN_SHARED_SECRET", "")
    # Token lifetime the Brain should mint (seconds); we enforce expiry on verify.
    SESSION_TTL_S: int = int(_req("SESSION_TTL_S", "2592000"))  # 30 days
    APP_NAME: str = "embodier-portal-api"


settings = Settings()
