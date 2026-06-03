"""
Review API — paid human code review workflow (user-facing only).

User endpoints:
  POST /api/v1/review/submit       — submit code for human review
  GET  /api/v1/review/my-requests  — check my review requests

Admin endpoints (pending, all, decide) moved to app/api/admin.py
on port 8002.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.db import get_conn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/review")


class SubmitReviewRequest(BaseModel):
    task_id: str
    notes: str = ""


@router.post("/submit")
async def submit_for_review(
    req: SubmitReviewRequest,
    user: dict = Depends(get_current_user),
):
    """Submit a generation task for human expert review."""
    conn = get_conn()

    task = conn.execute(
        "SELECT id, status FROM generation_tasks WHERE id = ? AND user_id = ?",
        (req.task_id, user["id"]),
    ).fetchone()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing = conn.execute(
        "SELECT id, status FROM review_requests WHERE task_id = ?",
        (req.task_id,),
    ).fetchone()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Review already requested (status: {existing['status']})",
        )

    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    needs_payment = bool(stripe_key)
    initial_status = "pending_payment" if needs_payment else "pending"

    conn.execute(
        "INSERT INTO review_requests (id, user_id, task_id, status, notes, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (review_id, user["id"], req.task_id, initial_status, req.notes, now, now),
    )
    conn.commit()

    log.info("Review request %s submitted by user %s (status=%s) for task %s",
             review_id, user["id"], initial_status, req.task_id)

    msg = "Payment required before review." if needs_payment else "Review submitted. An admin will review your code shortly."
    return {
        "review_id": review_id,
        "status": initial_status,
        "message": msg,
    }


@router.get("/my-requests")
async def get_my_reviews(
    user: dict = Depends(get_current_user),
):
    """Get the current user's review requests with task code + scan report."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT r.id, r.task_id, r.status, r.admin_feedback, r.admin_verdict, "
        "r.notes, r.created_at, r.updated_at, t.idea_text, t.language, "
        "t.generated_code "
        "FROM review_requests r "
        "JOIN generation_tasks t ON r.task_id = t.id "
        "WHERE r.user_id = ? "
        "ORDER BY r.created_at DESC",
        (user["id"],),
    ).fetchall()

    reviews = []
    for row in rows:
        review = {
            "id": row["id"],
            "task_id": row["task_id"],
            "status": row["status"],
            "admin_feedback": row["admin_feedback"],
            "admin_verdict": row["admin_verdict"],
            "notes": row["notes"],
            "idea": row["idea_text"],
            "language": row["language"],
            "code": row["generated_code"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        # Attach scan report for completed reviews
        if row["generated_code"]:
            scan = conn.execute(
                "SELECT report_json FROM scan_results WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
                (row["task_id"],),
            ).fetchone()
            if scan:
                try:
                    review["scan_report"] = json.loads(scan["report_json"])
                except (json.JSONDecodeError, TypeError):
                    review["scan_report"] = None
            else:
                review["scan_report"] = None
        else:
            review["scan_report"] = None

        reviews.append(review)

    return {"reviews": reviews}
