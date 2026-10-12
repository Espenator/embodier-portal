"""Embodier portal accounts API — member + broker panel backend."""
from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .db import init_db
from .routers import broker, course, member


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0")
    init_db()  # dev convenience: ensure tables exist on boot (idempotent)
    app.include_router(member.router)
    app.include_router(broker.router)
    app.include_router(course.router)

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "service": settings.APP_NAME}

    return app


app = create_app()
