"""
Shared fixtures for backend tests.

Uses _TEST_CONN override to bypass thread-local SQLite connections.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["CORS_ORIGINS"] = "*"

_TMP = Path(tempfile.mkdtemp(prefix="nexus_test_"))

# Patch unified DB path to use temp location
import app.db as _adb
_adb.DB_PATH = _TMP / "app.db"

# Init unified DB (creates ALL tables: v2 + auth + chat)
_adb.init_app_db()

# Pin the test connection so auth/chat delegates use it
import app.auth.auth as _aa
_aa._TEST_CONN = _adb.get_conn()

import app.api.chat_history as _ch
_ch._TEST_CONN = _adb.get_conn()

from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_db():
    """Truncate ALL tables before each test from the unified DB (FK-safe order)."""
    conn = _adb.get_conn()
    conn.executescript("""
        DELETE FROM sessions;
        DELETE FROM settings;
        DELETE FROM chat_messages;
        DELETE FROM shared_conversations;
        DELETE FROM chat_sessions;
        DELETE FROM team_members;
        DELETE FROM feature_requests;
        DELETE FROM review_requests;
        DELETE FROM code_assets;
        DELETE FROM scan_results;
        DELETE FROM generation_tasks;
        DELETE FROM teams;
        DELETE FROM users;
    """)
    conn.commit()
    # Reset in-memory rate limiter between tests
    _aa._LOGIN_ATTEMPTS.clear()


@pytest_asyncio.fixture
async def auth_headers() -> dict:
    """Create test user + JWT + session."""
    import pyotp
    from datetime import datetime, timezone
    from app.auth.auth import _hash_password, create_jwt

    conn = _aa._TEST_CONN
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute(
        "INSERT INTO users (username,email,totp_secret,password_hash,display_name,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("testuser", "test@test.com", pyotp.random_base32(), _hash_password("pw"), "Test User", now, now),
    )
    row = conn.execute("SELECT id,username FROM users WHERE username='testuser'").fetchone()
    assert row is not None

    token, jti, expires = create_jwt(row["id"], row["username"])
    conn.execute(
        "INSERT INTO sessions (user_id,token_jti,device_info,ip_address,created_at,expires_at) "
        "VALUES (?,?,?,?,?,?)",
        (row["id"], jti, "pytest", "", now, expires.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers() -> dict:
    """Create an admin user + JWT + session."""
    import pyotp
    from datetime import datetime, timezone
    from app.auth.auth import _hash_password, create_jwt

    conn = _aa._TEST_CONN
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute(
        "INSERT INTO users (username,email,totp_secret,password_hash,display_name,role,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("adminuser", "admin@test.com", pyotp.random_base32(), _hash_password("pw"), "Admin User", "admin", now, now),
    )
    row = conn.execute("SELECT id,username,role FROM users WHERE username='adminuser'").fetchone()
    assert row is not None and row["role"] == "admin"

    token, jti, expires = create_jwt(row["id"], row["username"], role="admin")
    conn.execute(
        "INSERT INTO sessions (user_id,token_jti,device_info,ip_address,created_at,expires_at) "
        "VALUES (?,?,?,?,?,?)",
        (row["id"], jti, "pytest", "", now, expires.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()
    return {"Authorization": f"Bearer {token}"}
