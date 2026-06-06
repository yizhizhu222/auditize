"""
Admin Application — runs on port 8002 (localhost only).

Provides admin auto-login and management endpoints without exposing
the admin interface to the internet.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.admin import router as admin_router

admin_app = FastAPI(title="Truffle Admin Panel")

admin_app.include_router(admin_router)

# Serve frontend SPA for admin
import os
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    admin_app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
