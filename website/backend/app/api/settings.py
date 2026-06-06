"""User settings, profile management, and avatar upload."""

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

router = APIRouter()


class SettingsUpdateRequest(BaseModel):
    settings: dict | None = None


class ProfileUpdateRequest(BaseModel):
    display_name: str = ""
    email: str = ""


@router.get("/api/v1/settings")
async def get_settings():
    """Get the current user's settings (API keys, model config, preferences)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.put("/api/v1/settings")
async def update_settings(request: SettingsUpdateRequest):
    """Update the current user's settings (merge strategy)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/settings/profile")
async def get_profile():
    """Get the current user's profile (display_name, email)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.put("/api/v1/settings/profile")
async def update_profile(request: ProfileUpdateRequest):
    """Update the current user's display name and email."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.post("/api/v1/settings/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    """Upload a profile avatar (PNG/JPG, max 2MB, validates dimensions)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/settings/sessions")
async def list_sessions():
    """List the current user's active sessions."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.delete("/api/v1/settings/sessions/{session_id}")
async def revoke_session(session_id: str):
    """Revoke a specific session (force logout)."""
    raise NotImplementedError("Full implementation available upon purchase")
