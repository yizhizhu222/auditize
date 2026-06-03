"""
Comprehensive tests for Review API, Settings API, Export API, and Generate API edge cases.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.auth.auth import _get_conn as auth_conn
from app.db import get_conn as app_conn


# ── Review API ─────────────────────────────────────────────────────────────────

class TestReview:
    """Expert review submission and admin decisions."""

    @pytest.mark.asyncio
    async def test_submit_review(self, client: AsyncClient, auth_headers: dict):
        """Submit a generation task for expert review."""
        uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
        conn = app_conn()
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'python', 'completed', ?, ?)",
            (task_id, uid, "Test idea", now, now),
        )
        conn.commit()

        resp = await client.post("/api/v1/review/submit", headers=auth_headers, json={
            "task_id": task_id,
            "notes": "Please review this code",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "review_id" in data

    @pytest.mark.asyncio
    async def test_submit_review_duplicate(self, client: AsyncClient, auth_headers: dict):
        """Submit same task twice should 409."""
        uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
        conn = app_conn()
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'python', 'completed', ?, ?)",
            (task_id, uid, "Dup review", now, now),
        )
        conn.commit()

        await client.post("/api/v1/review/submit", headers=auth_headers, json={
            "task_id": task_id,
        })
        resp = await client.post("/api/v1/review/submit", headers=auth_headers, json={
            "task_id": task_id,
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_review_nonexistent_task(self, client: AsyncClient, auth_headers: dict):
        """Submit review for non-existent task should 404."""
        resp = await client.post("/api/v1/review/submit", headers=auth_headers, json={
            "task_id": "nonexistent-task-id",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_my_reviews(self, client: AsyncClient, auth_headers: dict):
        """Get current user's review requests."""
        resp = await client.get("/api/v1/review/my-requests", headers=auth_headers)
        assert resp.status_code == 200
        assert "reviews" in resp.json()

    @pytest.mark.asyncio
    async def test_admin_pending(self, client: AsyncClient, admin_headers: dict):
        """Admin gets pending reviews."""
        resp = await client.get("/api/v1/review/pending", headers=admin_headers)
        assert resp.status_code == 200
        assert "pending" in resp.json()

    @pytest.mark.asyncio
    async def test_admin_decide_approve(self, client: AsyncClient, auth_headers: dict, admin_headers: dict):
        """Admin approves a review."""
        uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
        conn = app_conn()
        task_id = str(uuid.uuid4())
        review_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'python', 'completed', ?, ?)",
            (task_id, uid, "Review decision test", now, now),
        )
        conn.execute(
            "INSERT INTO review_requests (id, user_id, task_id, status, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?, ?)",
            (review_id, uid, task_id, "Check this", now, now),
        )
        conn.commit()

        resp = await client.put(f"/api/v1/review/{review_id}/decide",
                                headers=admin_headers,
                                json={"verdict": "approved", "feedback": "Looks good!"})
        assert resp.status_code == 200
        assert resp.json()["verdict"] == "approved"

    @pytest.mark.asyncio
    async def test_admin_decide_rejected(self, client: AsyncClient, auth_headers: dict, admin_headers: dict):
        """Admin rejects a review (status should be 'rejected', not 'completed')."""
        uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
        conn = app_conn()
        task_id = str(uuid.uuid4())
        review_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'python', 'completed', ?, ?)",
            (task_id, uid, "Reject test", now, now),
        )
        conn.execute(
            "INSERT INTO review_requests (id, user_id, task_id, status, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?, ?)",
            (review_id, uid, task_id, "Test", now, now),
        )
        conn.commit()

        resp = await client.put(f"/api/v1/review/{review_id}/decide",
                                headers=admin_headers,
                                json={"verdict": "rejected", "feedback": "Not safe"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_admin_decide_bad_verdict(self, client: AsyncClient, admin_headers: dict):
        """Bad verdict value should 400."""
        review_id = str(uuid.uuid4())
        resp = await client.put(f"/api/v1/review/{review_id}/decide",
                                headers=admin_headers,
                                json={"verdict": "invalid_verdict"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_all_reviews(self, client: AsyncClient, admin_headers: dict):
        """Admin gets all reviews."""
        resp = await client.get("/api/v1/review/all", headers=admin_headers)
        assert resp.status_code == 200
        assert "reviews" in resp.json()

    @pytest.mark.asyncio
    async def test_review_pending_requires_admin(self, client: AsyncClient, auth_headers: dict):
        """Non-admin cannot access pending reviews."""
        resp = await client.get("/api/v1/review/pending", headers=auth_headers)
        assert resp.status_code == 403


# ── Settings API ──────────────────────────────────────────────────────────────

class TestSettings:
    """User settings and profile."""

    @pytest.mark.asyncio
    async def test_get_settings(self, client: AsyncClient, auth_headers: dict):
        """Get settings (empty default)."""
        resp = await client.get("/api/v1/settings", headers=auth_headers)
        assert resp.status_code == 200
        assert "openAiKey" in resp.json()

    @pytest.mark.asyncio
    async def test_update_settings(self, client: AsyncClient, auth_headers: dict):
        """Update settings."""
        resp = await client.put("/api/v1/settings", headers=auth_headers, json={
            "systemPrompt": "You are a helpful assistant.",
            "maxHistoryMessages": 50,
        })
        assert resp.status_code == 200

        # Verify persistence
        resp = await client.get("/api/v1/settings", headers=auth_headers)
        data = resp.json()
        assert data["maxHistoryMessages"] == 50
        assert "helpful" in data["systemPrompt"]

    @pytest.mark.asyncio
    async def test_get_profile(self, client: AsyncClient, auth_headers: dict):
        """Get user profile."""
        resp = await client.get("/api/v1/settings/profile", headers=auth_headers)
        assert resp.status_code == 200
        assert "username" in resp.json()
        assert "display_name" in resp.json()

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """Update display name."""
        resp = await client.put("/api/v1/settings/profile", headers=auth_headers, json={
            "display_name": "Testy McTest",
        })
        assert resp.status_code == 200

        resp = await client.get("/api/v1/settings/profile", headers=auth_headers)
        assert resp.json()["display_name"] == "Testy McTest"

    @pytest.mark.asyncio
    async def test_list_sessions(self, client: AsyncClient, auth_headers: dict):
        """List active sessions."""
        resp = await client.get("/api/v1/settings/sessions", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()
        assert "total" in resp.json()

    @pytest.mark.asyncio
    async def test_revoke_session(self, client: AsyncClient, auth_headers: dict):
        """Revoke a session."""
        sessions = (await client.get("/api/v1/settings/sessions", headers=auth_headers)).json()
        if sessions["total"] > 0:
            sid = sessions["items"][0]["id"]
            resp = await client.delete(f"/api/v1/settings/sessions/{sid}", headers=auth_headers)
            assert resp.status_code == 200


# ── Export API ────────────────────────────────────────────────────────────────

class TestExport:
    """ZIP export of generated code."""

    @pytest.mark.asyncio
    async def test_export_zip(self, client: AsyncClient, auth_headers: dict):
        """Export a generation task as ZIP."""
        uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
        conn = app_conn()
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO generation_tasks (id, user_id, idea_text, generated_code, language, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'python', 'completed', ?, ?)",
            (task_id, uid, "Export test idea", "print('export me')", now, now),
        )
        conn.commit()

        resp = await client.get(f"/api/v1/export/{task_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

    @pytest.mark.asyncio
    async def test_export_nonexistent(self, client: AsyncClient, auth_headers: dict):
        """Export non-existent task should 404."""
        resp = await client.get("/api/v1/export/nonexistent-task-id", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_export_no_code(self, client: AsyncClient, auth_headers: dict):
        """Export task with no code should 400."""
        uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
        conn = app_conn()
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO generation_tasks (id, user_id, idea_text, generated_code, language, status, created_at, updated_at) "
            "VALUES (?, ?, ?, '', 'python', 'pending', ?, ?)",
            (task_id, uid, "No code", now, now),
        )
        conn.commit()

        resp = await client.get(f"/api/v1/export/{task_id}", headers=auth_headers)
        assert resp.status_code == 400


# ── Generate API ──────────────────────────────────────────────────────────────

class TestGenerate:
    """AI code generation edge cases."""

    @pytest.mark.asyncio
    async def test_generate_empty_idea(self, client: AsyncClient, auth_headers: dict):
        """Empty idea should 400."""
        resp = await client.post("/api/v1/generate", headers=auth_headers, json={
            "idea": "",
            "language": "python",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_no_api_key(self, client: AsyncClient, auth_headers: dict):
        """Missing API key should 400."""
        resp = await client.post("/api/v1/generate", headers=auth_headers, json={
            "idea": "A calculator",
            "language": "python",
            "api_key": "",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_list_tasks(self, client: AsyncClient, auth_headers: dict):
        """List generation tasks."""
        resp = await client.get("/api/v1/generate/tasks", headers=auth_headers)
        assert resp.status_code == 200
        assert "tasks" in resp.json()
        assert "total" in resp.json()

    @pytest.mark.asyncio
    async def test_generate_get_task_nonexistent(self, client: AsyncClient, auth_headers: dict):
        """Get non-existent task should 404."""
        resp = await client.get("/api/v1/generate/tasks/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404


# ── Admin API ─────────────────────────────────────────────────────────────────

class TestAdmin:
    """Admin user management and stats."""

    @pytest.mark.asyncio
    async def test_admin_list_users(self, client: AsyncClient, admin_headers: dict):
        """Admin lists users."""
        resp = await client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()
        assert "total" in resp.json()

    @pytest.mark.asyncio
    async def test_admin_stats(self, client: AsyncClient, admin_headers: dict):
        """Admin gets system stats."""
        resp = await client.get("/api/v1/admin/stats", headers=admin_headers)
        assert resp.status_code == 200
        assert "users" in resp.json()

    @pytest.mark.asyncio
    async def test_admin_non_admin_forbidden(self, client: AsyncClient, auth_headers: dict):
        """Non-admin cannot access admin APIs."""
        resp = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_change_role(self, client: AsyncClient, admin_headers: dict):
        """Admin changes user role."""
        users = (await client.get("/api/v1/admin/users", headers=admin_headers)).json()
        # Find a non-admin user
        non_admin = [u for u in users["items"] if u["role"] != "admin"]
        if non_admin:
            resp = await client.put(f"/api/v1/admin/users/{non_admin[0]['id']}/role",
                                    headers=admin_headers,
                                    json={"role": "admin"})
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_delete_user(self, client: AsyncClient, auth_headers: dict, admin_headers: dict):
        """Admin deletes a user."""
        # Register a sacrificial user
        await client.post("/api/v1/auth/register", json={
            "username": "sacrificial_lamb", "password": "Pass123456",
        })
        users = (await client.get("/api/v1/admin/users", headers=admin_headers)).json()
        target = [u for u in users["items"] if u["username"] == "sacrificial_lamb"]
        if target:
            resp = await client.delete(f"/api/v1/admin/users/{target[0]['id']}", headers=admin_headers)
            assert resp.status_code == 200


# ── System endpoints ───────────────────────────────────────────────────────────

class TestSystem:
    """Health, version, system status."""

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """Health check."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_version(self, client: AsyncClient):
        """Version info."""
        resp = await client.get("/api/v1/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    @pytest.mark.asyncio
    async def test_system_status(self, client: AsyncClient):
        """System status."""
        resp = await client.get("/api/v1/system/status")
        assert resp.status_code == 200
        assert "os" in resp.json()
