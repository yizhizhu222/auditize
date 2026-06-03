"""
Assets API — code asset library with duplicate detection.

When code is generated, it can be saved to the asset library.
When a user describes a new idea, the system checks if similar
code already exists — preventing duplicate development.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.db import get_conn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/assets")


class SaveAssetRequest(BaseModel):
    title: str
    description: str = ""
    language: str = "python"
    code: str = ""
    source_task_id: str = ""
    team_id: str = ""


@router.post("")
async def save_asset(
    req: SaveAssetRequest,
    user: dict = Depends(get_current_user),
):
    """Save generated code as a reusable asset in the library."""
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_conn()
    code_hash = hashlib.sha256(req.code.encode()).hexdigest()
    asset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    team_id = req.team_id.strip() if req.team_id.strip() else None

    # Check for duplicate — across the whole team if team_id is set
    if team_id:
        existing = conn.execute(
            "SELECT a.id, a.title, a.created_at FROM code_assets a "
            "JOIN team_members m ON a.user_id = m.user_id "
            "WHERE a.code_hash = ? AND m.team_id = ?",
            (code_hash, team_id),
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT id, title, created_at FROM code_assets WHERE code_hash = ? AND user_id = ?",
            (code_hash, user["id"]),
        ).fetchone()

    if existing:
        return {
            "asset_id": existing["id"],
            "duplicate": True,
            "message": f"This code already exists in your library as '{existing['title']}' (saved {existing['created_at']})",
        }

    conn.execute(
        "INSERT INTO code_assets (id, user_id, title, description, language, code_hash, source_task_id, team_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (asset_id, user["id"], req.title, req.description, req.language, code_hash,
         req.source_task_id or None, team_id, now),
    )
    conn.commit()

    return {
        "asset_id": asset_id,
        "duplicate": False,
        "message": "Code saved to your asset library.",
    }


@router.get("")
async def list_assets(
    language: str = Query("", description="Filter by language"),
    search: str = Query("", description="Search in title and description"),
    team_id: str = Query("", description="Filter by team (shows all team members' assets)"),
    user: dict = Depends(get_current_user),
):
    """List the current user's code assets, optionally filtered by team."""
    conn = get_conn()

    if team_id:
        # Show assets from all team members
        query = """SELECT a.* FROM code_assets a
                   JOIN team_members m ON a.user_id = m.user_id
                   WHERE m.team_id = ?"""
        params: list = [team_id]
    else:
        # Personal assets
        query = "SELECT * FROM code_assets WHERE user_id = ?"
        params = [user["id"]]

    if language:
        query += " AND language = ?"
        params.append(language)
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    assets = []
    for row in rows:
        assets.append({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "language": row["language"],
            "source_task_id": row["source_task_id"],
            "created_at": row["created_at"],
        })

    return {"assets": assets, "count": len(assets)}


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete an asset from the library."""
    conn = get_conn()
    result = conn.execute(
        "DELETE FROM code_assets WHERE id = ? AND user_id = ?",
        (asset_id, user["id"]),
    )
    conn.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Asset not found")

    return {"message": "Asset deleted"}


# ── Duplicate detection ──────────────────────────────────────────────────────

class SimilarityCheckRequest(BaseModel):
    idea: str
    language: str = ""
    team_id: str = ""


@router.post("/check-similar")
async def check_similar(
    req: SimilarityCheckRequest,
    user: dict = Depends(get_current_user),
):
    """
    Check if a new idea is similar to any existing assets.
    Uses text similarity on titles/descriptions to catch potential duplicates.
    """
    if not req.idea.strip():
        raise HTTPException(status_code=400, detail="Idea description cannot be empty")

    conn = get_conn()

    if req.language:
        rows = conn.execute(
            "SELECT id, title, description, language, created_at FROM code_assets "
            "WHERE user_id = ? AND language = ?",
            (user["id"], req.language),
        ).fetchall()
        if req.team_id:
            team_rows = conn.execute(
                "SELECT a.id, a.title, a.description, a.language, a.created_at FROM code_assets a "
                "JOIN team_members m ON a.user_id = m.user_id "
                "WHERE m.team_id = ? AND a.language = ? AND a.user_id != ?",
                (req.team_id, req.language, user["id"]),
            ).fetchall()
            rows = rows + team_rows
    else:
        rows = conn.execute(
            "SELECT id, title, description, language, created_at FROM code_assets WHERE user_id = ?",
            (user["id"],),
        ).fetchall()
        if req.team_id:
            team_rows = conn.execute(
                "SELECT a.id, a.title, a.description, a.language, a.created_at FROM code_assets a "
                "JOIN team_members m ON a.user_id = m.user_id "
                "WHERE m.team_id = ? AND a.user_id != ?",
                (req.team_id, user["id"]),
            ).fetchall()
            rows = rows + team_rows

    similar = []
    idea_lower = req.idea.lower()

    for row in rows:
        # Check title similarity
        title_sim = SequenceMatcher(None, idea_lower, (row["title"] or "").lower()).ratio()
        desc_sim = SequenceMatcher(None, idea_lower, (row["description"] or "").lower()).ratio()
        max_sim = max(title_sim, desc_sim)

        if max_sim > 0.4:  # 40%+ similarity threshold
            similar.append({
                "asset_id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "language": row["language"],
                "similarity": round(max_sim * 100),
                "created_at": row["created_at"],
            })

    # Sort by similarity descending
    similar.sort(key=lambda x: -x["similarity"])

    return {
        "has_similar": len(similar) > 0,
        "similar_assets": similar[:5],  # Top 5
    }
