"""
Settings API — per-user settings CRUD, profile management, session management.

All endpoints require JWT authentication (get_current_user dependency).
Settings are stored as a JSON blob in the auth.db `settings` table.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.auth.auth import _get_conn, get_current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings")


# ── Settings ────────────────────────────────────────────────────────────────────

class SettingsData(BaseModel):
    openAiKey: str = ""
    openRouterKey: str = ""
    deepSeekKey: str = ""
    anthropicKey: str = ""
    customBaseUrl: str = ""
    customApiKey: str = ""
    systemPrompt: str = ""
    maxHistoryMessages: int = 20
    activeModel: str = ""


@router.get("")
async def get_settings(user: dict = Depends(get_current_user)):
    """Get the current user's settings."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT settings_json FROM settings WHERE user_id = ?", (user["id"],)
    ).fetchone()
    if not row:
        return SettingsData().model_dump()
    try:
        data = json.loads(row["settings_json"])
        return SettingsData(**data).model_dump()
    except (json.JSONDecodeError, TypeError):
        return SettingsData().model_dump()


@router.put("")
async def update_settings(
    settings: SettingsData,
    user: dict = Depends(get_current_user),
):
    """Update the current user's settings (merge with existing)."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read existing
    existing = {}
    row = conn.execute(
        "SELECT settings_json FROM settings WHERE user_id = ?", (user["id"],)
    ).fetchone()
    if row:
        try:
            existing = json.loads(row["settings_json"])
        except (json.JSONDecodeError, TypeError):
            existing = {}

    # Merge — skip empty-string fields so we don't overwrite existing values
    new_data = {k: v for k, v in settings.model_dump(exclude_unset=True).items()
                if v != "" or k in ("maxHistoryMessages",)}
    merged = {**existing, **new_data}

    conn.execute(
        """INSERT INTO settings (user_id, settings_json, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET settings_json = ?, updated_at = ?""",
        (user["id"], json.dumps(merged, ensure_ascii=False), now,
         json.dumps(merged, ensure_ascii=False), now),
    )
    conn.commit()
    log.info("Settings updated for user %s", user["username"])
    return {"status": "ok"}


# ── Profile ─────────────────────────────────────────────────────────────────────

class ProfileData(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get the current user's profile."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, email, display_name, role, avatar_url, created_at FROM users WHERE id = ?",
        (user["id"],),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@router.put("/profile")
async def update_profile(
    profile: ProfileData,
    user: dict = Depends(get_current_user),
):
    """Update display_name and/or email."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updates = []
    params = []
    if profile.display_name is not None:
        updates.append("display_name = ?")
        params.append(profile.display_name)
    if profile.email is not None:
        updates.append("email = ?")
        params.append(profile.email)
    if not updates:
        return {"status": "ok"}
    updates.append("updated_at = ?")
    params.append(now)
    params.append(user["id"])
    conn.execute(
        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    log.info("Profile updated for user %s", user["username"])
    return {"status": "ok"}


AVATAR_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "avatars"


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload an avatar image (PNG/JPG, max 2MB)."""
    if not file.content_type or file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Only PNG/JPG allowed")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = "png" if file.content_type == "image/png" else "jpg"
    filename = f"user_{user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
    path = AVATAR_DIR / filename
    path.write_bytes(content)

    avatar_url = f"/static/avatars/{filename}"
    conn = _get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE users SET avatar_url = ?, updated_at = ? WHERE id = ?",
        (avatar_url, now, user["id"]),
    )
    conn.commit()
    return {"avatar_url": avatar_url}


# ── Sessions ────────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    """List all active sessions for the current user."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT id, token_jti, device_info, ip_address, created_at, expires_at
           FROM sessions
           WHERE user_id = ? AND expires_at > datetime('now')
           ORDER BY created_at DESC""",
        (user["id"],),
    ).fetchall()
    return {
        "total": len(rows),
        "items": [dict(r) for r in rows],
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    """Revoke a specific session (only if it belongs to the current user)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    log.info("Session %s revoked for user %s", session_id, user["username"])
    return {"status": "ok"}