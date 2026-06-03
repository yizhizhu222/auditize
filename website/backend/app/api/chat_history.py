"""
Chat History API — persistent multi-session chat storage.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.db import get_conn

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat")

_LOCAL = threading.local()
_TEST_CONN = None


def _get_conn() -> sqlite3.Connection:
    global _TEST_CONN
    if _TEST_CONN is not None:
        return _TEST_CONN
    return get_conn()


def init_chat_db() -> None:
    """Tables are created by init_app_db() in db.py — no-op here."""
    pass


# ── Models ──

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class SessionOut(BaseModel):
    id: int
    title: str
    message_count: int
    created_at: str
    updated_at: str


class SessionCreate(BaseModel):
    title: str = "新对话"


class SessionUpdate(BaseModel):
    title: str


class MessageSend(BaseModel):
    session_id: int
    role: str = "user"
    content: str


# ── Session CRUD ──

@router.get("/sessions", summary="List all chat sessions for the current user")
async def list_sessions(user: dict = Depends(get_current_user)):
    conn = _get_conn()
    rows = conn.execute(
        """SELECT s.*, (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) as message_count
           FROM chat_sessions s WHERE s.user_id = ?
           ORDER BY s.updated_at DESC""",
        (user["id"],),
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/sessions", summary="Create a new chat session")
async def create_session(req: SessionCreate, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        "INSERT INTO chat_sessions (title, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (req.title, user["id"], now, now),
    )
    conn.commit()
    return {"id": cur.lastrowid, "title": req.title, "message_count": 0, "created_at": now, "updated_at": now}


@router.put("/sessions/{session_id}", summary="Update session title")
async def update_session(session_id: int, req: SessionUpdate, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (req.title, now, session_id, user["id"]),
    )
    if conn.total_changes == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    conn.commit()
    return {"status": "ok"}


@router.delete("/sessions/{session_id}", summary="Delete a chat session and all its messages")
async def delete_session(session_id: int, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user["id"]))
    if conn.total_changes == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    conn.commit()
    return {"status": "ok"}


# ── Messages ──

@router.get("/sessions/{session_id}/messages", summary="Get messages for a session")
async def get_messages(session_id: int, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    # Verify ownership
    session = conn.execute(
        "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = conn.execute(
        "SELECT id, role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/sessions/{session_id}/messages", summary="Add a message to a session")
async def add_message(session_id: int, msg: MessageSend, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    # Verify ownership
    session = conn.execute(
        "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, msg.role, msg.content, now),
    )
    # Update session timestamp
    conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    return {"id": cur.lastrowid, "role": msg.role, "content": msg.content, "created_at": now}

# ── Share conversation to team ────────────────────────────────────────────────

class ShareRequest(BaseModel):
    session_id: int
    title: str = ""


@router.post("/share", summary="Share an AI conversation to the team")
async def share_conversation(req: ShareRequest, user: dict = Depends(get_current_user)):
    """Share a chat session to the team chat."""
    conn = _get_conn()
    # Verify ownership
    session = conn.execute(
        "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
        (req.session_id, int(user["id"])),
    ).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Count messages
    count = conn.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
        (req.session_id,),
    ).fetchone()[0]
    if count == 0:
        raise HTTPException(status_code=400, detail="No messages to share")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        "INSERT INTO shared_conversations (title, session_id, shared_by, message_count, created_at) VALUES (?, ?, ?, ?, ?)",
        (req.title or "\u5171\u4eab\u5bf9\u8bdd", req.session_id, user["username"], count, now),
    )
    conn.commit()
    share_id = cur.lastrowid

    # Note: WebSocket team chat was removed in v2, so we skip WS broadcast.
    # The share is persisted in the database \u2014 that's sufficient.
    # (WebSocket team chat broadcast was removed in v2)

    return {"id": share_id, "status": "ok"}


@router.get("/shared", summary="List shared conversations")
async def list_shared(page: int = 1, per_page: int = 20):
    conn = _get_conn()
    offset = (page - 1) * per_page
    total = conn.execute("SELECT COUNT(*) FROM shared_conversations").fetchone()[0]
    rows = conn.execute(
        "SELECT id, title, session_id, shared_by, message_count, created_at "
        "FROM shared_conversations ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    return {"total": total, "page": page, "items": [dict(r) for r in rows]}


@router.get("/shared/{share_id}", summary="Get shared conversation details with messages")
async def get_shared(share_id: int):
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, title, session_id, shared_by, message_count, created_at "
        "FROM shared_conversations WHERE id = ?", (share_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Shared conversation not found")
    data = dict(row)
    # Get the messages
    msgs = conn.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
        (data["session_id"],),
    ).fetchall()
    data["messages"] = [dict(m) for m in msgs]
    return data


# ── Online users & chat history (from WebSocket) ──────────────────────────────

# ── /online and /history endpoints removed in v2 (team chat was removed) ─────

@router.get("/search", summary="Search chat sessions and messages")
async def search_chat(
    q: str = "",
    user: dict = Depends(get_current_user),
):
    """Search across the current user's chat sessions and messages."""
    if not q.strip():
        return {"sessions": [], "messages": []}
    conn = _get_conn()
    term = f"%{q.strip()}%"

    # Search sessions by title
    sessions = conn.execute(
        "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? AND title LIKE ? ORDER BY updated_at DESC LIMIT 20",
        (user["id"], term),
    ).fetchall()

    # Search messages in user's sessions
    messages = conn.execute(
        """SELECT m.id, m.session_id, m.role, m.content, m.created_at, s.title as session_title
           FROM chat_messages m
           JOIN chat_sessions s ON m.session_id = s.id
           WHERE s.user_id = ? AND m.content LIKE ?
           ORDER BY m.created_at DESC LIMIT 30""",
        (user["id"], term),
    ).fetchall()

    return {
        "sessions": [dict(r) for r in sessions],
        "messages": [dict(r) for r in messages],
    }
