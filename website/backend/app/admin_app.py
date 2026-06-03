"""
Admin FastAPI app — runs on 127.0.0.1:8002, NOT exposed to the internet.

Only admin-level APIs live here: user management, review decisions,
data browser, system stats. Everything that require_admin() protects.
"""

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.auth import init_auth_db
from app.api.chat_history import init_chat_db
from app.api.admin import init_admin_db, router as admin_router
from app.db import init_app_db, get_conn as get_app_conn

# ── Frontend dist path (same as main app) ───────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "Nexus AI" / "dist"

# ── Load .env ────────────────────────────────────────────────
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# ── Config ───────────────────────────────────────────────────
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ── Logging ──────────────────────────────────────────────────
log_formatter = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG if DEBUG else LOG_LEVEL)
root_logger.addHandler(console_handler)

log = logging.getLogger(__name__)


@asynccontextmanager
async def admin_lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Same DB init as main app — shares the same app.db."""
    init_auth_db()
    init_chat_db()
    init_admin_db()
    init_app_db()
    from app.db import migrate_from_legacy
    migrate_from_legacy()
    log.info("Admin app ready — sharing app.db with main app")
    yield
    log.info("Admin app shutting down")


app = FastAPI(title="Truffle Admin", version="1.0.0", debug=DEBUG, lifespan=admin_lifespan)

# ── CORS (allow requests from main app frontend) ────────────
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
# Also allow the main app port so admin frontend can call via localhost
origins.append("http://localhost:8001")
origins.append("https://trufflekit.com")
origins.append("https://www.trufflekit.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log.info("Admin CORS allowed origins: %s", origins)


@app.exception_handler(Exception)
async def admin_exception_handler(request: Request, exc: Exception):
    log.exception("Admin unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Auto-login for admin frontend (no password, localhost-only) ──
@app.get("/api/v1/admin/auto-login")
async def admin_auto_login():
    """Return a JWT for the admin user. Safe because this only listens on 127.0.0.1."""
    from app.auth.auth import create_jwt
    conn = get_app_conn()
    admin_user = conn.execute(
        "SELECT id, username, role FROM users WHERE role='admin' ORDER BY id ASC LIMIT 1"
    ).fetchone()
    if not admin_user:
        return JSONResponse(status_code=500, content={"detail": "No admin user found"})
    token, jti, expires = create_jwt(admin_user["id"], admin_user["username"], role="admin")
    # Also save session
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR IGNORE INTO sessions (user_id, token_jti, device_info, ip_address, created_at, expires_at) "
        "VALUES (?, ?, 'auto-login (admin port)', '127.0.0.1', ?, ?)",
        (admin_user["id"], jti, now, expires.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()
    return {"access_token": token, "token_type": "bearer", "role": "admin", "username": admin_user["username"]}


# ── Routers (admin-only) ────────────────────────────────────
app.include_router(admin_router)   # user mgmt, reviews, data browser, stats


# ── Serve frontend (same dist as main app) ──────────────────
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="admin_assets")

    @app.exception_handler(StarletteHTTPException)
    async def admin_spa_fallback(request: Request, exc):
        if exc.status_code == 404 and not request.url.path.startswith("/api/"):
            return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

    @app.get("/")
    async def serve_admin_frontend():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")

    log.info("Admin serving frontend from %s (port 8002)", FRONTEND_DIST)
