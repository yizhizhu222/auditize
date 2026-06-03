"""
Notifications API — unread count, list, mark read.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.auth import get_current_user
from app.db import get_conn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications")


def create_notification(
    user_id: int,
    type: str,
    title: str,
    message: str = "",
    related_id: str = "",
) -> int | None:
    """Insert a notification for a user. Returns the new row id or None on failure."""
    try:
        conn = get_conn()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO notifications (user_id, type, title, message, related_id, is_read, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (user_id, type, title, message, related_id, now),
        )
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except Exception as e:
        log.warning("Failed to create notification: %s", e)
        return None


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """List notifications for the current user, newest first."""
    conn = get_conn()
    if unread_only:
        rows = conn.execute(
            "SELECT id, type, title, message, related_id, is_read, created_at "
            "FROM notifications WHERE user_id = ? AND is_read = 0 "
            "ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, type, title, message, related_id, is_read, created_at "
            "FROM notifications WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit),
        ).fetchall()

    return {
        "notifications": [
            {
                "id": r["id"],
                "type": r["type"],
                "title": r["title"],
                "message": r["message"],
                "related_id": r["related_id"],
                "is_read": bool(r["is_read"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    }


@router.get("/unread-count")
async def unread_count(
    user: dict = Depends(get_current_user),
):
    """Return the number of unread notifications."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND is_read = 0",
        (user["id"],),
    ).fetchone()
    return {"count": row["cnt"]}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    user: dict = Depends(get_current_user),
):
    """Mark a single notification as read."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM notifications WHERE id = ? AND user_id = ?",
        (notification_id, user["id"]),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()
    return {"status": "ok"}


@router.put("/read-all")
async def mark_all_read(
    user: dict = Depends(get_current_user),
):
    """Mark all notifications as read for the current user."""
    conn = get_conn()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
        (user["id"],),
    )
    conn.commit()
    return {"status": "ok"}
