"""CampusConnect AI - FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .database import SessionLocal, init_db
from .routers import admin, ai, auth, complaints, notifications, reports
from .seed import backfill_notifications_if_empty, ensure_admin, seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        ensure_admin(db)
        if config.AUTO_SEED:
            seed_if_empty(db)
        backfill_notifications_if_empty(db)
    yield


app = FastAPI(
    title="CampusConnect AI",
    version="1.0.0",
    description=(
        "University lost & found and complaint management. "
        "AI matching is a suggestion; a human verifies every match."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(complaints.router)
app.include_router(admin.router)
app.include_router(ai.router)
app.include_router(notifications.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": "CampusConnect AI", "version": app.version}


app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

# Serve the web client last so /api and /uploads take precedence.
if config.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
