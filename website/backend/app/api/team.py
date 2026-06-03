"""
Team API — multi-team support.

A user can be a member of multiple teams.
Each team has: owner, reviewer(s), member(s).
Roles are per-team, not global.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.db import get_conn
from app.api.notifications import create_notification

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/team")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_username(user_id: int) -> str:
    from app.auth.auth import _get_conn as auth_conn
    try:
        conn = auth_conn()
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["username"] if row else f"User#{user_id}"
    except Exception:
        return f"User#{user_id}"


def _get_team_ids(user_id: int) -> list[str]:
    """Get all team_ids for a user."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT team_id FROM team_members WHERE user_id = ?", (user_id,)
    ).fetchall()
    return [r["team_id"] for r in rows]


def _get_members(team_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id, role FROM team_members WHERE team_id = ?", (team_id,)
    ).fetchall()
    members = []
    for r in rows:
        members.append({
            "user_id": r["user_id"],
            "username": _get_username(r["user_id"]),
            "role": r["role"],
        })
    return members


def _verify_membership(team_id: str, user_id: int) -> str | None:
    """Return the user's role in the team, or None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
        (team_id, user_id),
    ).fetchone()
    return row["role"] if row else None


# ── Team CRUD ────────────────────────────────────────────────────────────────

class CreateTeamRequest(BaseModel):
    name: str
    description: str = ""


@router.post("/create")
async def create_team(req: CreateTeamRequest, user: dict = Depends(get_current_user)):
    """Create a new team. The creator becomes the owner. One user can be in many teams."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Team name is required")

    team_id = str(uuid.uuid4())
    invite_code = secrets.token_hex(6)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_conn()
    conn.execute(
        "INSERT INTO teams (id, name, description, invite_code, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (team_id, req.name.strip(), req.description.strip(), invite_code, user["id"], now),
    )
    conn.execute(
        "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'owner')",
        (team_id, user["id"]),
    )
    conn.commit()

    log.info("Team %s created by user %s", team_id, user["id"])

    return {"team_id": team_id, "name": req.name, "invite_code": invite_code}


@router.get("/list")
async def list_teams(user: dict = Depends(get_current_user)):
    """Return all teams the current user belongs to."""
    team_ids = _get_team_ids(user["id"])
    if not team_ids:
        return {"teams": []}

    conn = get_conn()
    placeholders = ",".join("?" for _ in team_ids)
    rows = conn.execute(
        f"SELECT * FROM teams WHERE id IN ({placeholders})", team_ids
    ).fetchall()

    teams = []
    for t in rows:
        role = _verify_membership(t["id"], user["id"])
        teams.append({
            "team_id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "invite_code": t["invite_code"] if role == "owner" else None,
            "my_role": role,
            "created_at": t["created_at"],
        })

    return {"teams": teams}


@router.get("/my")
async def get_my_team(
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """Get a specific team's info and members. If no team_id given, returns first team."""
    team_ids = _get_team_ids(user["id"])
    if not team_ids:
        return {"in_team": False}

    # If no team_id specified, use first team
    tid = team_id if team_id else team_ids[0]

    conn = get_conn()
    team = conn.execute("SELECT * FROM teams WHERE id = ?", (tid,)).fetchone()
    if not team:
        return {"in_team": False}

    role = _verify_membership(tid, user["id"])
    if not role:
        # User requested a team they're not in
        raise HTTPException(status_code=403, detail="You are not a member of this team")

    members = _get_members(tid)

    return {
        "in_team": True,
        "team_id": team["id"],
        "name": team["name"],
        "description": team["description"],
        "invite_code": team["invite_code"] if role == "owner" else None,
        "created_by": team["created_by"],
        "created_at": team["created_at"],
        "members": members,
        "my_role": role,
    }


class JoinTeamRequest(BaseModel):
    invite_code: str


@router.post("/join")
async def join_team(req: JoinTeamRequest, user: dict = Depends(get_current_user)):
    """Join a team using an invite code. One user can join many teams."""
    if not req.invite_code.strip():
        raise HTTPException(status_code=400, detail="Invite code is required")

    conn = get_conn()
    team = conn.execute(
        "SELECT id, name FROM teams WHERE invite_code = ?", (req.invite_code.strip(),)
    ).fetchone()
    if not team:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Check if already a member
    existing = _verify_membership(team["id"], user["id"])
    if existing:
        raise HTTPException(status_code=409, detail="You are already a member of this team")

    conn.execute(
        "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'member')",
        (team["id"], user["id"]),
    )
    conn.commit()

    return {"team_id": team["id"], "name": team["name"], "role": "member"}


@router.post("/regenerate-invite")
async def regenerate_invite(
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """(Owner) Generate a new invite code for the team."""
    team_ids = _get_team_ids(user["id"])
    tid = team_id if team_id else (team_ids[0] if team_ids else None)
    if not tid:
        raise HTTPException(status_code=400, detail="You are not in a team")

    role = _verify_membership(tid, user["id"])
    if role != "owner":
        raise HTTPException(status_code=403, detail="Owner role required")

    new_code = secrets.token_hex(6)
    conn = get_conn()
    conn.execute("UPDATE teams SET invite_code = ? WHERE id = ?", (new_code, tid))
    conn.commit()
    return {"invite_code": new_code}


@router.post("/disband")
async def disband_team(
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """(Owner) Permanently delete the team."""
    team_ids = _get_team_ids(user["id"])
    tid = team_id if team_id else (team_ids[0] if team_ids else None)
    if not tid:
        raise HTTPException(status_code=400, detail="You are not in a team")

    role = _verify_membership(tid, user["id"])
    if role != "owner":
        raise HTTPException(status_code=403, detail="Owner role required")

    conn = get_conn()
    conn.execute("DELETE FROM feature_requests WHERE team_id = ?", (tid,))
    conn.execute("DELETE FROM team_members WHERE team_id = ?", (tid,))
    conn.execute("DELETE FROM teams WHERE id = ?", (tid,))
    conn.commit()

    log.info("Team %s disbanded by user %s", tid, user["id"])
    return {"message": "Team disbanded"}


@router.post("/leave")
async def leave_team(
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """Leave a team. Owner cannot leave (disband instead)."""
    team_ids = _get_team_ids(user["id"])
    tid = team_id if team_id else (team_ids[0] if team_ids else None)
    if not tid:
        raise HTTPException(status_code=400, detail="You are not in a team")

    role = _verify_membership(tid, user["id"])
    if role == "owner":
        raise HTTPException(status_code=400, detail="Owner cannot leave. Disband the team instead.")

    conn = get_conn()
    conn.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?", (tid, user["id"]))
    conn.commit()
    return {"message": "Left the team"}


@router.post("/change-role")
async def change_role(
    target_user_id: int,
    new_role: str,
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """(Owner) Change a member's role."""
    if new_role not in ("member", "reviewer", "owner"):
        raise HTTPException(status_code=400, detail="Invalid role")

    team_ids = _get_team_ids(user["id"])
    tid = team_id if team_id else (team_ids[0] if team_ids else None)
    if not tid:
        raise HTTPException(status_code=400, detail="You are not in a team")

    role = _verify_membership(tid, user["id"])
    if role != "owner":
        raise HTTPException(status_code=403, detail="Owner role required")

    conn = get_conn()
    target = conn.execute(
        "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
        (tid, target_user_id),
    ).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not in your team")

    conn.execute(
        "UPDATE team_members SET role = ? WHERE team_id = ? AND user_id = ?",
        (new_role, tid, target_user_id),
    )
    conn.commit()

    return {"message": f"User {target_user_id} role changed to {new_role}"}


# ── Feature Requests ─────────────────────────────────────────────────────────

class NewRequest(BaseModel):
    title: str
    description: str = ""


@router.post("/requests")
async def create_request(
    req: NewRequest,
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """Submit a new feature request to a specific team."""
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    team_ids = _get_team_ids(user["id"])
    tid = team_id if team_id else (team_ids[0] if team_ids else None)
    if not tid:
        raise HTTPException(status_code=400, detail="You are not in a team")

    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_conn()
    conn.execute(
        "INSERT INTO feature_requests (id, team_id, user_id, title, description, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
        (request_id, tid, user["id"], req.title.strip(), req.description.strip(), now, now),
    )
    conn.commit()

    # ── Auto check similarity against team's existing assets ──
    similar_assets = []
    try:
        assets = conn.execute(
            "SELECT a.id, a.title, a.description, a.language FROM code_assets a "
            "JOIN team_members m ON a.user_id = m.user_id "
            "WHERE m.team_id = ?",
            (tid,),
        ).fetchall()
        idea_lower = (req.title + " " + req.description).lower()
        for a in assets:
            title_sim = SequenceMatcher(None, idea_lower, (a["title"] or "").lower()).ratio()
            desc_sim = SequenceMatcher(None, idea_lower, (a["description"] or "").lower()).ratio()
            max_sim = max(title_sim, desc_sim)
            if max_sim > 0.4:
                similar_assets.append({
                    "asset_id": a["id"],
                    "title": a["title"],
                    "language": a["language"],
                    "similarity": round(max_sim * 100),
                })
        similar_assets.sort(key=lambda x: -x["similarity"])
    except Exception as e:
        log.warning("Similarity check failed on request submit: %s", e)

    log.info("Request %s created by user %s (similar_assets=%d)", request_id, user["id"], len(similar_assets))

    return {
        "request_id": request_id,
        "status": "pending",
        "similar_assets": similar_assets[:3],  # Top 3 warnings
        "has_similar": len(similar_assets) > 0,
    }


@router.get("/requests")
async def list_requests(
    status: str = Query("all", pattern="^(all|pending|approved|generating|completed|rejected|duplicate)$"),
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """List feature requests for a specific team."""
    team_ids = _get_team_ids(user["id"])
    tid = team_id if team_id else (team_ids[0] if team_ids else None)
    if not tid:
        return {"requests": []}

    conn = get_conn()

    if status == "all":
        rows = conn.execute(
            "SELECT r.*, t.idea_text, t.generated_code "
            "FROM feature_requests r "
            "LEFT JOIN generation_tasks t ON r.linked_task_id = t.id "
            "WHERE r.team_id = ? "
            "ORDER BY r.created_at DESC",
            (tid,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT r.*, t.idea_text, t.generated_code "
            "FROM feature_requests r "
            "LEFT JOIN generation_tasks t ON r.linked_task_id = t.id "
            "WHERE r.team_id = ? AND r.status = ? "
            "ORDER BY r.created_at DESC",
            (tid, status),
        ).fetchall()

    requests = []
    for row in rows:
        requests.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "username": _get_username(row["user_id"]),
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "linked_task_id": row["linked_task_id"],
            "duplicate_of": row["duplicate_of"],
            "reviewer_notes": row["reviewer_notes"],
            "code": row["generated_code"] or "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return {"requests": requests}


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single feature request."""
    # Find which team this request belongs to
    conn = get_conn()
    row = conn.execute(
        "SELECT r.*, t.idea_text, t.generated_code, t.language "
        "FROM feature_requests r "
        "LEFT JOIN generation_tasks t ON r.linked_task_id = t.id "
        "WHERE r.id = ?",
        (request_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Request not found")

    # Verify user is a member of the team
    role = _verify_membership(row["team_id"], user["id"])
    if not role:
        raise HTTPException(status_code=403, detail="You are not a member of this team")

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "username": _get_username(row["user_id"]),
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "linked_task_id": row["linked_task_id"],
        "duplicate_of": row["duplicate_of"],
        "reviewer_notes": row["reviewer_notes"],
        "code": row["generated_code"] or "",
        "language": row["language"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class ReviewRequestDecision(BaseModel):
    decision: str
    notes: str = ""
    duplicate_of: str = ""


@router.put("/requests/{request_id}/review")
async def review_request(
    request_id: str,
    req: ReviewRequestDecision,
    team_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """(Reviewer) Review a feature request."""
    if req.decision not in ("approved", "rejected", "duplicate"):
        raise HTTPException(status_code=400, detail="Decision must be: approved, rejected, or duplicate")

    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM feature_requests WHERE id = ?",
        (request_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")

    # Verify user is a reviewer in the team
    role = _verify_membership(row["team_id"], user["id"])
    if role not in ("reviewer", "owner"):
        raise HTTPException(status_code=403, detail="Reviewer or owner role required")
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {row['status']}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if req.decision == "duplicate":
        conn.execute(
            "UPDATE feature_requests SET status = 'duplicate', duplicate_of = ?, reviewer_notes = ?, updated_at = ? WHERE id = ?",
            (req.duplicate_of, req.notes, now, request_id),
        )
    else:
        new_status = "approved" if req.decision == "approved" else "rejected"
        conn.execute(
            "UPDATE feature_requests SET status = ?, reviewer_notes = ?, updated_at = ? WHERE id = ?",
            (new_status, req.notes, now, request_id),
        )

    conn.commit()

    # ── Notify the request submitter ──
    try:
        status_labels = {"approved": "approved ✅", "rejected": "rejected ❌", "duplicate": "marked as duplicate 📎"}
        reviewer_name = _get_username(user["id"])
        notif_title = f"Request {status_labels.get(req.decision, req.decision)}"
        notif_msg = f'"{row["title"]}" was {req.decision} by {reviewer_name}'
        create_notification(
            user_id=row["user_id"],
            type=req.decision,
            title=notif_title,
            message=notif_msg,
            related_id=request_id,
        )
    except Exception as e:
        log.warning("Failed to create notification for request %s: %s", request_id, e)

    return {"status": req.decision}


@router.post("/requests/{request_id}/generate")
async def generate_for_request(
    request_id: str,
    team_id: str = Query(""),
    language: str = Query("python", description="Target language: python, javascript, go, cpp"),
    user: dict = Depends(get_current_user),
):
    """(Reviewer) Generate code for an approved feature request."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM feature_requests WHERE id = ?",
        (request_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")

    role = _verify_membership(row["team_id"], user["id"])
    if role not in ("reviewer", "owner"):
        raise HTTPException(status_code=403, detail="Reviewer or owner role required")
    if row["status"] not in ("pending", "approved"):
        raise HTTPException(status_code=409, detail=f"Cannot generate for request in '{row['status']}' state")

    idea = f"{row['title']}\n\n{row['description']}" if row['description'] else row['title']
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute(
        "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'generating', ?, ?)",
        (task_id, user["id"], idea, language, now, now),
    )
    conn.execute(
        "UPDATE feature_requests SET status = 'generating', linked_task_id = ?, updated_at = ? WHERE id = ?",
        (task_id, now, request_id),
    )
    conn.commit()

    return {"task_id": task_id, "idea": idea, "message": "Generation task created."}


@router.post("/requests/{request_id}/link-task")
async def link_task_to_request(
    request_id: str,
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """(Reviewer) Link a completed generation task to a feature request."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM feature_requests WHERE id = ?",
        (request_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")

    role = _verify_membership(row["team_id"], user["id"])
    if role not in ("reviewer", "owner"):
        raise HTTPException(status_code=403, detail="Reviewer or owner role required")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE feature_requests SET status = 'completed', linked_task_id = ?, updated_at = ? WHERE id = ?",
        (task_id, now, request_id),
    )
    conn.commit()

    return {"status": "completed"}
