"""Settings loaded from backend/.env (real environment variables win)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

load_dotenv(BACKEND_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DATA_DIR = Path(os.getenv("DATA_DIR") or (BACKEND_DIR / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"sqlite:///{(DATA_DIR / 'campusconnect.db').as_posix()}"
)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "720"))

ADMIN_NAME = os.getenv("ADMIN_NAME", "Campus Administrator")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@campus.edu").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!")

AUTO_SEED = _bool("AUTO_SEED", True)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
