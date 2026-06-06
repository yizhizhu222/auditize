"""
Truffle AI Platform — Main Application Entry Point

This module initializes the FastAPI application, configures middleware,
registers all API routers, and serves the frontend SPA.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as health_router
from app.api.generate import router as generate_router
from app.api.scan import router as scan_router
from app.api.review import router as review_router
from app.api.payment import router as payment_router
from app.api.assets import router as assets_router
from app.api.chat import router as chat_router
from app.api.chat_history import router as chat_history_router
from app.api.compile import router as compile_router
from app.api.settings import router as settings_router
from app.api.admin import router as admin_router
from app.api.team import router as team_router
from app.api.export import router as export_router
from app.api.notifications import router as notifications_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — initialize services on startup, clean up on shutdown."""
    raise NotImplementedError("Full implementation available upon purchase")
    yield


app = FastAPI(
    title="Truffle AI Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://trufflekit.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that returns a JSON error response."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Full implementation available upon purchase."},
    )


# ── Register routers ─────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(generate_router)
app.include_router(scan_router)
app.include_router(review_router)
app.include_router(payment_router)
app.include_router(assets_router)
app.include_router(chat_router)
app.include_router(chat_history_router)
app.include_router(compile_router)
app.include_router(settings_router)
app.include_router(admin_router)
app.include_router(team_router)
app.include_router(export_router)
app.include_router(notifications_router)


# ── Static files (avatars) ───────────────────────────────────────────────────
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")


# ── SPA fallback ─────────────────────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
