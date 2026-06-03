"""
Nexus AI v2 — FastAPI backend entry point.

CORS · Logging · Global exception handler
Refocused on: idea→code generation + security scanning + expert review.
"""

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# ⚠ Load .env BEFORE app module imports — many modules read env vars at import time
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from app.api.routes import router
from app.auth import router as auth_router
from app.auth.auth import init_auth_db
from app.api.chat import router as chat_router
from app.api.settings import router as settings_router
from app.api.chat_history import router as chat_history_router, init_chat_db
from app.api.compile import router as compile_router

# v2 new modules
from app.api.generate import router as generate_router
from app.api.scan import router as scan_router
from app.api.review import router as review_router
from app.api.assets import router as assets_router
from app.api.team import router as team_router
from app.api.export import router as export_router
from app.api.payment import router as payment_router
from app.api.notifications import router as notifications_router
from app.db import init_app_db

# ── Frontend dist path ─────────────────────────────────────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "Nexus AI" / "dist"

# ── Config from environment ──────────────────────────────────────────────────
PROJECT_NAME    = os.getenv("PROJECT_NAME", "Truffle AI Platform")
VERSION         = os.getenv("VERSION", "1.0.0")
DEBUG           = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE        = os.getenv("LOG_FILE", str(Path(__file__).resolve().parent.parent.parent / "logs" / "backend-app.log"))

# ── Logging ──────────────────────────────────────────────────────────────────
log_formatter = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

file_handler = RotatingFileHandler(
    Path(LOG_FILE) if os.path.isabs(LOG_FILE) else Path(__file__).resolve().parent.parent / LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG if DEBUG else LOG_LEVEL)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

log = logging.getLogger(__name__)
log.info("Logging initialised — writing to %s", LOG_FILE)

# ── FastAPI app ──────────────────────────────────────────────────────────────
# ── Lifespan: startup / shutdown ──────────────────────────────────────────────
@asynccontextmanager
async def app_lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Startup: init DBs, create default user. Shutdown: cleanup."""
    # ── Startup ──
    init_auth_db()
    init_chat_db()
    init_app_db()  # v2 unified tables (now includes auth + chat tables)
    # Migrate data from legacy auth.db / chat_history.db to unified app.db
    from app.db import migrate_from_legacy
    migrate_from_legacy()
    from app.auth.auth import _get_conn
    conn = _get_conn()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    from app.auth.auth import _hash_password
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_pw = _hash_password(admin_password)
    if admin_password == "admin123":
        log.warning("Using default admin password 'admin123'. Set ADMIN_PASSWORD in .env for production.")
    conn.execute(
        "INSERT OR IGNORE INTO users (username, email, totp_secret, password_hash, display_name, role, created_at, updated_at) "
        "VALUES ('admin', 'admin@nexus.local', '', ?, 'Admin', 'admin', ?, ?)",
        (admin_pw, now, now),
    )
    conn.commit()
    log.info("Unified DB ready — admin user present")
    log.info("%s v2 started (debug=%s)", PROJECT_NAME, DEBUG)
    yield
    # ── Shutdown ──
    log.info("Server shutting down")


app = FastAPI(title=PROJECT_NAME, version=VERSION, debug=DEBUG, lifespan=app_lifespan)

# ── CORS (allow frontend dev server) ─────────────────────────────────────────
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,https://trufflekit.com,https://www.trufflekit.com").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log.info("CORS allowed origins: %s", origins)

# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
        },
    )

# ── Serve uploaded files (avatars) ────────────────────────────────────────────
data_dir = Path(__file__).resolve().parent.parent / "data"
avatars_dir = data_dir / "avatars"
avatars_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=str(avatars_dir)), name="avatars")

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(router)              # health, version, system/status
app.include_router(auth_router)          # login, register, JWT
app.include_router(chat_router)          # AI completions proxy
app.include_router(chat_history_router)  # chat sessions, history
app.include_router(settings_router)      # user settings/profile
app.include_router(compile_router)       # code sandbox

# v2 core modules
app.include_router(generate_router)      # idea → code generation
app.include_router(scan_router)          # code security scanning
app.include_router(review_router)        # human review workflow
app.include_router(assets_router)        # code asset library
app.include_router(team_router)          # team + feature requests
app.include_router(export_router)        # ZIP download / deploy
app.include_router(payment_router)       # Stripe Checkout / payment
app.include_router(notifications_router) # user notifications


# ── Serve frontend static files ─────────────────────────────────────────────
if FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

    # Serve root-level static assets (logo, favicon, PWA files)
    _ROOT_FILES = {
        "/logo.png":           "image/png",
        "/favicon.png":        "image/png",
        "/pwa-icon.svg":       "image/svg+xml",
        "/pwa-192x192.png":    "image/png",
        "/pwa-512x512.png":    "image/png",
        "/apple-touch-icon.png": "image/png",
        "/manifest.webmanifest": "application/manifest+json",
    }
    for _path, _mime in _ROOT_FILES.items():
        _fp = str(FRONTEND_DIST / _path.lstrip("/"))
        if Path(_fp).exists():
            # Use add_api_route to avoid signature issues with closures
            app.add_api_route(_path, lambda fp=_fp, mt=_mime: FileResponse(fp, media_type=mt),
                              include_in_schema=False, methods=["GET"])

    NO_CACHE_HEADERS = {
        "Cache-Control": "no-cache, no-store, must-revalidate, private, max-age=0",
        "CDN-Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request: Request, exc):
        if exc.status_code == 404 and not request.url.path.startswith("/api/"):
            return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html",
                                headers=dict(NO_CACHE_HEADERS))
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html",
                            headers=dict(NO_CACHE_HEADERS))

    # Never cache service worker files — they MUST be fresh
    @app.get("/sw.js")
    async def serve_sw():
        return FileResponse(str(FRONTEND_DIST / "sw.js"), media_type="application/javascript",
                            headers=dict(NO_CACHE_HEADERS))

    @app.get("/workbox-{rest:path}")
    async def serve_workbox(rest: str):
        fp = FRONTEND_DIST / f"workbox-{rest}"
        if fp.exists():
            return FileResponse(str(fp), media_type="application/javascript",
                                headers=dict(NO_CACHE_HEADERS))
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    log.info("Serving frontend from %s", FRONTEND_DIST)
else:
    @app.get("/")
    async def root():
        return {
            "project": PROJECT_NAME,
            "version": VERSION,
            "debug": DEBUG,
            "docs": "/docs",
        }