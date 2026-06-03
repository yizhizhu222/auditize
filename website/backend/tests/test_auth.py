"""
Tests for auth endpoints: register, login, verify, logout, refresh,
change-password, delete-account, TOTP setup, OAuth connections.
"""

import pytest
from httpx import AsyncClient


class TestAuth:
    """Authentication & user management."""

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """Smoke test — /health should always work."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Register a new user."""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "Pass123456",
            "email": "new@test.com",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient):
        """Register with a duplicate username should fail."""
        await client.post("/api/v1/auth/register", json={
            "username": "dupuser", "password": "Pass123456",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "username": "dupuser", "password": "Pass123456",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Password < 8 chars should be rejected."""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "user1", "password": "Abc1234",
        })
        assert resp.status_code == 400

    # ── Login with password ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_login_with_password(self, client: AsyncClient):
        """Register then login with password should work."""
        await client.post("/api/v1/auth/register", json={
            "username": "loginuser", "password": "Test123456",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "loginuser", "password": "Test123456",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_login_invalid_code(self, client: AsyncClient):
        """A wrong TOTP code should 401."""
        resp = await client.post("/api/v1/auth/login", json={"token": "123456"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_bad_format(self, client: AsyncClient):
        """Non-numeric token should 400."""
        resp = await client.post("/api/v1/auth/login", json={"token": "abcdef"})
        assert resp.status_code == 400

    # ── JWT verification ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, client: AsyncClient, auth_headers: dict):
        """Verify a valid JWT."""
        resp = await client.post("/api/v1/auth/verify", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_verify_no_token(self, client: AsyncClient):
        """Verify without token should 401."""
        resp = await client.post("/api/v1/auth/verify")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_fake_token(self, client: AsyncClient):
        """Verify with a garbage token should 401."""
        resp = await client.post("/api/v1/auth/verify",
                                 headers={"Authorization": "Bearer fake.jwt.token"})
        assert resp.status_code == 401

    # ── User profile ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_me(self, client: AsyncClient, auth_headers: dict):
        """GET /me should return user profile."""
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["username"]) > 0

    # ── Logout & Refresh ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers: dict):
        """Logout should revoke the session."""
        resp = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 200

        # Token should no longer work
        resp = await client.post("/api/v1/auth/verify", headers=auth_headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, auth_headers: dict):
        """Refresh should return a new token."""
        resp = await client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["expires_in"] > 0

    # ── TOTP ─────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_totp_setup(self, client: AsyncClient, auth_headers: dict):
        """TOTP setup should return a secret and provisioning URI."""
        resp = await client.post("/api/v1/auth/totp/setup", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["secret"]) > 10
        assert "otpauth://" in data["provisioning_uri"]

    # ── Change password ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient):
        """Change password with correct old password."""
        await client.post("/api/v1/auth/register", json={
            "username": "pwuser99", "password": "Oldpass123",
        })
        # Create JWT + session for the registered user
        from app.auth.auth import _get_conn, create_jwt
        from datetime import datetime, timezone
        conn = _get_conn()
        row = conn.execute("SELECT id, username FROM users ORDER BY id").fetchone()
        token, jti, expires = create_jwt(row["id"], row["username"])
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO sessions (user_id,token_jti,device_info,ip_address,created_at,expires_at) VALUES (?,?,?,?,?,?)",
            (row["id"], jti, "pytest", "", now, expires.strftime("%Y-%m-%dT%H:%M:%SZ"))
        )
        conn.commit()
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post("/api/v1/auth/change-password", headers=headers, json={
            "old_password": "Oldpass123", "new_password": "Newpass456",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client: AsyncClient, auth_headers: dict):
        """Change password with wrong old password should 401."""
        resp = await client.post("/api/v1/auth/change-password", headers=auth_headers, json={
            "old_password": "wrongpass",
            "new_password": "Newpass456",
        })
        assert resp.status_code == 401 or resp.status_code == 404

    # ── OAuth connections ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_oauth_connect_disconnect(self, client: AsyncClient, auth_headers: dict):
        """OAuth connect/disconnect round-trip."""
        resp = await client.post("/api/v1/auth/connections/github/connect", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["connected"] is True

        resp = await client.get("/api/v1/auth/connections", headers=auth_headers)
        github = [c for c in resp.json()["connections"] if c["provider"] == "github"]
        assert len(github) == 1
        assert github[0]["connected"] is True

        resp = await client.post("/api/v1/auth/connections/github/disconnect", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["connected"] is False

    @pytest.mark.asyncio
    async def test_oauth_unknown_provider(self, client: AsyncClient, auth_headers: dict):
        """Unknown provider should 400."""
        resp = await client.post("/api/v1/auth/connections/bitbucket/connect", headers=auth_headers)
        assert resp.status_code == 400

    # ── Delete account ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_account(self, client: AsyncClient):
        """Delete account should remove the user."""
        await client.post("/api/v1/auth/register", json={
            "username": "deluser456", "password": "Delpass123456",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "deluser456", "password": "Delpass123456",
        })
        assert resp.status_code == 200
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        resp = await client.post("/api/v1/auth/delete-account", headers=headers)
        assert resp.status_code == 200

        # Token should no longer work
        resp = await client.post("/api/v1/auth/verify", headers=headers)
        assert resp.status_code == 401
