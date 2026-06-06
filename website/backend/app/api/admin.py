"""Admin API — user management, review decisions, data browser, and system stats."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class UserRoleUpdateRequest(BaseModel):
    role: str


class ReviewDecisionRequest(BaseModel):
    decision: str
    notes: str = ""


# ── Auth ─────────────────────────────────────────────────────────────────────

@router.get("/api/v1/admin/auto-login")
async def admin_auto_login():
    """
    Auto-login endpoint for the admin application (localhost:8002 only).
    
    Returns a JWT for the admin user without password verification.
    Safe because this endpoint is only accessible from localhost.
    """
    raise NotImplementedError("Full implementation available upon purchase")


# ── Users ────────────────────────────────────────────────────────────────────

@router.get("/api/v1/admin/users")
async def list_users(page: int = 1, per_page: int = 20):
    """List all users with pagination."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.put("/api/v1/admin/users/{user_id}/role")
async def change_user_role(user_id: int, request: UserRoleUpdateRequest):
    """Change a user's role (admin/reviewer/user)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.delete("/api/v1/admin/users/{user_id}")
async def delete_user(user_id: int):
    """Delete a user and all associated data (cascade cleanup)."""
    raise NotImplementedError("Full implementation available upon purchase")


# ── Reviews ──────────────────────────────────────────────────────────────────

@router.get("/api/v1/admin/reviews/pending")
async def pending_reviews():
    """List all pending review requests with code and user notes."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.put("/api/v1/admin/reviews/{review_id}/decide")
async def decide_review(review_id: str, request: ReviewDecisionRequest):
    """Make a decision on a review request (approved/changes_needed/rejected)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/admin/reviews/all")
async def all_reviews(status: str = ""):
    """List all review requests with optional status filter."""
    raise NotImplementedError("Full implementation available upon purchase")


# ── System ───────────────────────────────────────────────────────────────────

@router.get("/api/v1/admin/stats")
async def system_stats():
    """Return system statistics (users, sessions, tasks, scans, teams)."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/admin/db-tables")
async def list_tables():
    """List all database tables with schemas and row counts."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/admin/db-tables/{table_name}")
async def browse_table(table_name: str, page: int = 1, per_page: int = 50):
    """Browse table data with pagination (SQL-injection-safe via whitelist)."""
    raise NotImplementedError("Full implementation available upon purchase")
