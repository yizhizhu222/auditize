"""
Admin API — user management, review decisions, data browser, system stats.

All endpoints require admin role. Runs on 127.0.0.1:8002 (not exposed to internet).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.auth import get_current_user, require_admin, _get_conn as auth_conn
from app.db import get_conn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin")

def init_admin_db():
    """Admin DB init — no extra tables needed."""
    log.info("Admin DB initialised")

# ═══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users", summary="List all users (admin only)")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    conn = auth_conn()
    offset = (page - 1) * per_page
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    rows = conn.execute(
        "SELECT id, username, email, display_name, role, avatar_url, created_at, updated_at "
        "FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    return {"total": total, "page": page, "items": [dict(r) for r in rows]}


class UpdateUserRole(BaseModel):
    role: str


@router.put("/users/{user_id}/role", summary="Change user role (admin only)")
async def update_user_role(
    user_id: int,
    req: UpdateUserRole,
    admin: dict = Depends(require_admin),
):
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    conn = auth_conn()
    row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    if int(row["id"]) == int(admin["id"]):
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
                 (req.role, now, user_id))
    conn.commit()
    return {"status": "ok", "user_id": user_id, "role": req.role}


@router.delete("/users/{user_id}", summary="Delete a user (admin only)")
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_admin),
):
    if int(user_id) == int(admin["id"]):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    conn = auth_conn()
    app_conn = get_conn()
    row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    # Cascade delete: app.db tables (user references)
    # 1. scan_results for this user's generation tasks
    task_ids = [r["id"] for r in app_conn.execute(
        "SELECT id FROM generation_tasks WHERE user_id = ?", (user_id,)
    ).fetchall()]
    for tid in task_ids:
        app_conn.execute("DELETE FROM scan_results WHERE task_id = ?", (tid,))
    # 2. generation_tasks
    app_conn.execute("DELETE FROM generation_tasks WHERE user_id = ?", (user_id,))
    # 3. review_requests
    app_conn.execute("DELETE FROM review_requests WHERE user_id = ?", (user_id,))
    # 4. code_assets
    app_conn.execute("DELETE FROM code_assets WHERE user_id = ?", (user_id,))
    # 5. feature_requests
    app_conn.execute("DELETE FROM feature_requests WHERE user_id = ?", (user_id,))
    # 6. team_memberships for this user
    app_conn.execute("DELETE FROM team_members WHERE user_id = ?", (user_id,))
    # 7. teams this user created (clean members first)
    created_team_ids = [r["id"] for r in app_conn.execute(
        "SELECT id FROM teams WHERE created_by = ?", (user_id,)
    ).fetchall()]
    for tid in created_team_ids:
        app_conn.execute("DELETE FROM team_members WHERE team_id = ?", (tid,))
        app_conn.execute("DELETE FROM feature_requests WHERE team_id = ?", (tid,))
        app_conn.execute("DELETE FROM teams WHERE id = ?", (tid,))

    # Auth tables
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    app_conn.commit()
    return {"status": "ok", "message": f"User {user_id} and all associated data deleted"}


@router.get("/stats", summary="Global system stats (admin only)")
async def system_stats(admin: dict = Depends(require_admin)):
    conn = auth_conn()
    app_conn = get_conn()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
    total_tasks = app_conn.execute("SELECT COUNT(*) FROM generation_tasks").fetchone()[0]
    total_scans = app_conn.execute("SELECT COUNT(*) FROM scan_results").fetchone()[0]
    total_teams = app_conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    return {
        "users": {"total": total_users, "admin": admin_count, "active_sessions": total_sessions},
        "content": {"generation_tasks": total_tasks, "scan_results": total_scans},
        "teams": {"total": total_teams},
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  REVIEW MANAGEMENT (admin-only, moved from review.py)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_username(user_id: int) -> str:
    """Look up a username by user_id."""
    try:
        conn = auth_conn()
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["username"] if row else f"User#{user_id}"
    except Exception as e:
        log.error("Failed to get username for user_id=%s: %s", user_id, e)
        return f"User#{user_id}"


@router.get("/reviews/pending", summary="List pending reviews (admin only)")
async def get_pending_reviews(admin: dict = Depends(require_admin)):
    """Get all pending review requests."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT r.id, r.user_id, r.task_id, r.status, r.notes, "
        "r.created_at, t.idea_text, t.language, t.generated_code "
        "FROM review_requests r "
        "JOIN generation_tasks t ON r.task_id = t.id "
        "WHERE r.status = 'pending' "
        "ORDER BY r.created_at ASC",
    ).fetchall()

    pending = []
    for row in rows:
        pending.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "username": _get_username(row["user_id"]),
            "task_id": row["task_id"],
            "notes": row["notes"],
            "idea": row["idea_text"],
            "language": row["language"],
            "code": row["generated_code"],
            "submitted_at": row["created_at"],
        })

    return {"pending": pending}


class ReviewDecision(BaseModel):
    verdict: str
    feedback: str = ""


@router.put("/reviews/{review_id}/decide", summary="Decide on a review (admin only)")
async def decide_review(
    review_id: str,
    decision: ReviewDecision,
    admin: dict = Depends(require_admin),
):
    """Approve, reject, or request changes for a review."""
    if decision.verdict not in ("approved", "changes_needed", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Verdict must be one of: approved, changes_needed, rejected",
        )

    conn = get_conn()
    review = conn.execute(
        "SELECT * FROM review_requests WHERE id = ?", (review_id,)
    ).fetchone()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Review is already {review['status']}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status_map = {"approved": "completed", "changes_needed": "changes_needed", "rejected": "rejected"}
    new_status = status_map.get(decision.verdict, "completed")
    conn.execute(
        "UPDATE review_requests SET status = ?, admin_feedback = ?, "
        "admin_verdict = ?, assigned_to = ?, updated_at = ? WHERE id = ?",
        (new_status, decision.feedback, decision.verdict, admin["id"], now, review_id),
    )
    conn.commit()

    log.info("Review %s decided as '%s' (status=%s) by admin %s",
             review_id, decision.verdict, new_status, admin["id"])

    return {"review_id": review_id, "status": new_status, "verdict": decision.verdict, "feedback": decision.feedback}


@router.get("/reviews/all", summary="List all reviews (admin only)")
async def get_all_reviews(
    status_filter: str = Query("all", pattern="^(all|pending|completed)$"),
    admin: dict = Depends(require_admin),
):
    """Get all review requests, optionally filtered by status."""
    conn = get_conn()

    if status_filter == "all":
        rows = conn.execute(
            "SELECT r.*, t.idea_text, t.language "
            "FROM review_requests r "
            "JOIN generation_tasks t ON r.task_id = t.id "
            "ORDER BY r.created_at DESC",
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT r.*, t.idea_text, t.language "
            "FROM review_requests r "
            "JOIN generation_tasks t ON r.task_id = t.id "
            "WHERE r.status = ? "
            "ORDER BY r.created_at DESC",
            (status_filter,),
        ).fetchall()

    reviews = []
    for row in rows:
        reviews.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "username": _get_username(row["user_id"]),
            "task_id": row["task_id"],
            "status": row["status"],
            "verdict": row["admin_verdict"],
            "feedback": row["admin_feedback"],
            "notes": row["notes"],
            "idea": row["idea_text"],
            "language": row["language"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return {"reviews": reviews, "count": len(reviews)}


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA BROWSER — browse all database tables without writing SQL
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tables", summary="List all database tables and their columns")
async def list_tables(admin: dict = Depends(require_admin)):
    """List all tables in app.db with their column schemas."""
    conn = get_conn()
    raw = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()

    tables = []
    for row in raw:
        name = row["name"]
        cols = conn.execute(f"PRAGMA table_info(`{name}`)").fetchall()
        columns = [{"name": c["name"], "type": c["type"], "notnull": bool(c["notnull"]), "pk": bool(c["pk"])} for c in cols]
        row_count = conn.execute(f"SELECT COUNT(*) as c FROM `{name}`").fetchone()["c"]
        tables.append({"name": name, "columns": columns, "row_count": row_count})

    return {"tables": tables}


@router.get("/table/{name}", summary="Browse a table's data with pagination")
async def browse_table(
    name: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str = Query("", max_length=200),
    admin: dict = Depends(require_admin),
):
    """Read rows from a table with pagination and optional search."""
    # Whitelist: only allow known table names (prevent SQL injection)
    conn = get_conn()
    known = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    if not known:
        raise HTTPException(status_code=404, detail=f"Table '{name}' not found")

    offset = (page - 1) * per_page

    # Get total count
    total = conn.execute(f"SELECT COUNT(*) as c FROM `{name}`").fetchone()["c"]

    # Get columns
    cols = conn.execute(f"PRAGMA table_info(`{name}`)").fetchall()
    col_names = [c["name"] for c in cols]

    # Get data
    rows = conn.execute(
        f"SELECT * FROM `{name}` LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()

    return {
        "table": name,
        "columns": col_names,
        "rows": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  PAYMENT CONFIG (for admin frontend)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/payment/config", summary="Payment configuration for frontend")
async def admin_payment_config(admin: dict = Depends(require_admin)):
    """Return payment config (admin view)."""
    import os
    stripe_key = bool(os.environ.get("STRIPE_SECRET_KEY", ""))
    price = os.environ.get("PAYMENT_PRICE_USD", "29")
    return {
        "configured": stripe_key,
        "price_dollars": f"${price}.00",
        "price_cents": int(price) * 100,
    }
