"""
Auth — TOTP login, JWT issue/verify, session management.

Database: data/app.db (unified)
  - users:    id, username, email, totp_secret, display_name, avatar_url, role,
              created_at, updated_at, email_verified, locked_until
  - sessions: id, user_id, token_jti, device_info, ip_address, created_at, expires_at
  - settings: user_id (PK), settings_json, updated_at
  - verification_codes: id, email, code, purpose, used, expires_at, created_at
  - login_attempts: id, username, ip_address, success, attempted_at
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import bcrypt
import jwt as pyjwt
import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.db import get_conn as get_app_conn
from app.email_utils import send_verification_code

log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 168  # 7 days

_LOCAL = threading.local()
_TEST_CONN = None
router = APIRouter(prefix="/api/v1/auth")
security = HTTPBearer(auto_error=False)  # optional bearer for verify/me


# ── Connection (delegates to unified app.db) ──────────────────────────────────
def _get_conn() -> sqlite3.Connection:
    global _TEST_CONN
    if _TEST_CONN is not None:
        return _TEST_CONN
    return get_app_conn()


def init_auth_db() -> None:
    """Tables are created by init_app_db() in db.py — no-op here."""
    pass


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (includes embedded salt)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash. Supports both bcrypt and legacy SHA-256."""
    if not hashed:
        return False
    # bcrypt format starts with "$2b$" or "$2a$"
    if hashed.startswith("$2"):
        return bcrypt.checkpw(password.encode(), hashed.encode())
    # Legacy SHA-256 format: "salt$hexdigest"
    if "$" in hashed:
        salt, expected = hashed.split("$", 1)
        actual = hashlib.sha256((salt + password).encode()).hexdigest()
        return actual == expected
    return False


def _validate_password_strength(password: str) -> Optional[str]:
    """Check password strength. Returns an error message or None."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain an uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain a lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain a digit"
    return None


# ── Simple in-memory rate limiter (per IP) ──────────────────────────────────
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_RATE_LIMIT = 5  # max attempts
_LOGIN_RATE_WINDOW = 60  # seconds


def _check_login_rate(ip: str) -> None:
    """Raises HTTPException 429 if rate limit exceeded."""
    now = time.time()
    window_start = now - _LOGIN_RATE_WINDOW
    if ip in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[ip] = [t for t in _LOGIN_ATTEMPTS[ip] if t > window_start]
    else:
        _LOGIN_ATTEMPTS[ip] = []
    if len(_LOGIN_ATTEMPTS[ip]) >= _LOGIN_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    _LOGIN_ATTEMPTS[ip].append(now)


# ── Email validation ────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _validate_email(email: str) -> Optional[str]:
    """Check email format. Returns error message or None."""
    if not email or not email.strip():
        return "Email address cannot be empty"
    if not _EMAIL_RE.match(email.strip()):
        return "Invalid email format"
    disallowed_prefixes = ("mailinator", "guerrillamail", "tempmail", "10minutemail")
    domain = email.strip().lower().split("@")[1]
    for p in disallowed_prefixes:
        if p in domain:
            return "Temporary email providers are not supported"
    return None


# ── Persistent account lockout ─────────────────────────────────────────────
_ACCOUNT_LOCK_MINUTES = 15
_ACCOUNT_MAX_FAILURES = 5
_VERIFICATION_CODE_EXPIRE_MINUTES = 10
_RESEND_COOLDOWN_SECONDS = 60


def _record_login_attempt(username: str, ip: str, success: bool) -> None:
    """Insert a login attempt record."""
    conn = get_app_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO login_attempts (username, ip_address, success, attempted_at) VALUES (?, ?, ?, ?)",
        (username.lower().strip(), ip, 1 if success else 0, now),
    )
    conn.commit()


def _count_recent_failures(username: str) -> int:
    """Count consecutive failed attempts in the last 30 minutes."""
    conn = get_app_conn()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = conn.execute(
        "SELECT success FROM login_attempts WHERE username = ? AND attempted_at > ? ORDER BY attempted_at DESC LIMIT ?",
        (username.lower().strip(), cutoff, _ACCOUNT_MAX_FAILURES),
    ).fetchall()
    count = 0
    for r in rows:
        if r["success"]:
            break
        count += 1
    return count


def _check_account_locked(username: str) -> None:
    """Raise 423 if account is locked."""
    conn = get_app_conn()
    row = conn.execute(
        "SELECT locked_until FROM users WHERE LOWER(username) = ?", (username.lower().strip(),)
    ).fetchone()
    if not row:
        return
    locked_until = row["locked_until"] or ""
    if locked_until:
        try:
            locked_dt = datetime.fromisoformat(locked_until)
            if locked_dt > datetime.now(timezone.utc):
                remaining = int((locked_dt - datetime.now(timezone.utc)).total_seconds())
                raise HTTPException(
                    status_code=423,
                    detail=f"Account locked. Please try again in {remaining // 60} minutes.",
                )
        except ValueError:
            pass


def _lock_account(username: str) -> None:
    """Set a lock on the account."""
    conn = get_app_conn()
    until = (datetime.now(timezone.utc) + timedelta(minutes=_ACCOUNT_LOCK_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE users SET locked_until = ? WHERE LOWER(username) = ?", (until, username.lower().strip()))
    conn.commit()
    log.warning("Account '%s' locked until %s", username, until)


# ── JWT helpers ──────────────────────────────────────────────────────────────────
def create_jwt(user_id: int, username: str, role: str = "user") -> tuple[str, str, datetime]:
    """Create a JWT and return (token, jti, expires_at)."""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, expires


def decode_jwt(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        return pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def _is_session_active(jti: str) -> bool:
    """Check if a JTI is still in the sessions table."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM sessions WHERE token_jti = ? AND expires_at > datetime('now')",
        (jti,),
    ).fetchone()
    return row is not None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency: extract and validate JWT, return user info."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    payload = decode_jwt(credentials.credentials)
    if not _is_session_active(payload["jti"]):
        raise HTTPException(status_code=401, detail="Session revoked or expired")
    return {
        "id": payload["sub"],
        "username": payload["username"],
        "role": payload.get("role", "user"),
        "jti": payload["jti"],
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Like get_current_user but returns None instead of 401 when no token."""
    if credentials is None:
        return None
    try:
        payload = decode_jwt(credentials.credentials)
        if _is_session_active(payload["jti"]):
            return {
                "id": payload["sub"],
                "username": payload["username"],
                "role": payload.get("role", "user"),
                "jti": payload["jti"],
            }
    except HTTPException:
        pass
    return None


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency: ensure the current user has admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Endpoints ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    token: str = ""   # 6-digit TOTP (mutually exclusive with username+password)
    username: str = ""
    password: str = ""


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_HOURS * 3600
    user: dict
    role: str = "user"


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    """Login with either TOTP (token) or username+password."""
    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate(client_ip)
    conn = _get_conn()
    found = None
    login_username = req.username.strip().lower() if req.username else ""
    login_failed_reason = ""

    # ── Account lockout check ──────────────────────────────────────────
    if login_username:
        _check_account_locked(login_username)

    # ── Password login ───────────────────────────────────────────────────
    if login_username and req.password:
        row = conn.execute(
            "SELECT id, username, display_name, role, password_hash FROM users WHERE LOWER(username) = ?",
            (login_username,),
        ).fetchone()
        if row and _verify_password(req.password, row["password_hash"]):
            found = dict(row)
        if found is None:
            _record_login_attempt(login_username, client_ip, False)
            failures = _count_recent_failures(login_username)
            if failures >= _ACCOUNT_MAX_FAILURES:
                _lock_account(login_username)
                raise HTTPException(status_code=423, detail="Too many failed attempts. Account locked for 15 minutes.")
            raise HTTPException(status_code=401, detail="Invalid username or password")
    # ── TOTP login ──────────────────────────────────────────────────────
    else:
        if len(req.token) != 6 or not req.token.isdigit():
            raise HTTPException(status_code=400, detail="Token must be a 6-digit number")
        if req.username:
            # Username provided: query that specific user
            row = conn.execute(
                "SELECT id, username, display_name, role, totp_secret FROM users WHERE LOWER(username) = ?",
                (req.username.strip().lower(),),
            ).fetchone()
            if row:
                totp = pyotp.TOTP(row["totp_secret"])
                if totp.verify(req.token, valid_window=1):
                    found = dict(row)
        else:
            # Pure TOTP login — find the matching user (fallback for UI convenience)
            for row in conn.execute("SELECT id, username, display_name, role, totp_secret FROM users").fetchall():
                totp = pyotp.TOTP(row["totp_secret"])
                if totp.verify(req.token, valid_window=1):
                    found = dict(row)
                    break
        if found is None:
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    role = found.get("role", "user") if isinstance(found, dict) else "user"
    token, jti, expires = create_jwt(found["id"], found["username"], role=role)

    # Record successful login (clears failure count)
    if login_username:
        _record_login_attempt(login_username, client_ip, True)
        conn.execute("UPDATE users SET locked_until = '' WHERE LOWER(username) = ?", (login_username.lower().strip(),))

    # Record session
    device_info = request.headers.get("User-Agent", "")[:200]
    conn.execute(
        """INSERT INTO sessions (user_id, token_jti, device_info, ip_address, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (found["id"], jti, device_info, "",
         datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         expires.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()

    return LoginResponse(
        access_token=token,
        role=role,
        user={
            "id": found["id"],
            "username": found["username"],
            "display_name": found["display_name"] or found["username"],
        },
    )


@router.get("/verify")
@router.post("/verify")
async def verify(user: dict = Depends(get_current_user)):
    """Verify that the current JWT is valid. Used on frontend reload."""
    return {"status": "ok", "user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    """Return current user profile."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, email, display_name, role, avatar_url, created_at, email_verified FROM users WHERE id = ?",
        (user["id"],),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Revoke the current session."""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE token_jti = ?", (user["jti"],))
    conn.commit()
    log.info("User '%s' logged out (session %s)", user["username"], user["jti"][:8])
    return {"status": "ok"}


@router.post("/refresh")
async def refresh_token(user: dict = Depends(get_current_user)):
    """Issue a new JWT and revoke the old one (graceful rotation)."""
    conn = _get_conn()
    # Create new token
    new_token, new_jti, expires = create_jwt(user["id"], user["username"])
    # Revoke old
    conn.execute("DELETE FROM sessions WHERE token_jti = ?", (user["jti"],))
    # Insert new session
    conn.execute(
        """INSERT INTO sessions (user_id, token_jti, device_info, ip_address, created_at, expires_at)
           VALUES (?, ?, '', '', ?, ?)""",
        (user["id"], new_jti,
         datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         expires.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()
    return {"access_token": new_token, "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600}


@router.post("/totp/setup")
async def totp_setup(user: dict = Depends(get_current_user)):
    """Generate a new TOTP secret for the current user (re-enrollment)."""
    conn = _get_conn()
    new_secret = pyotp.random_base32()
    totp = pyotp.TOTP(new_secret)
    provisioning_uri = totp.provisioning_uri(name=user["username"], issuer_name="Truffle AI")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE users SET totp_secret = ?, updated_at = ? WHERE id = ?",
        (new_secret, now, user["id"]),
    )
    conn.commit()
    return {"secret": new_secret, "provisioning_uri": provisioning_uri}


@router.post("/totp/verify-setup")
async def totp_verify_setup(
    req: LoginRequest,
    user: dict = Depends(get_current_user),
):
    """Verify a TOTP code against the user's current secret (confirm setup)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT totp_secret FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    totp = pyotp.TOTP(row["totp_secret"])
    if totp.verify(req.token, valid_window=2):
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail="Invalid TOTP code, please try again")


# ── Register / Change password / Delete account ──────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""
    invite_code: str = ""


@router.post("/register")
async def register(req: RegisterRequest):
    """Create a new user account. Email is optional but recommended for verification."""
    # Normalize inputs
    username = req.username.strip().lower()
    email = req.email.strip().lower()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    pw_error = _validate_password_strength(req.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)
    if email:
        email_error = _validate_email(email)
        if email_error:
            raise HTTPException(status_code=400, detail=email_error)

    conn = _get_conn()

    # Validate invite_code if provided — must match a valid team
    invited_team = None
    if req.invite_code.strip():
        team = conn.execute(
            "SELECT id, name FROM teams WHERE invite_code = ?", (req.invite_code.strip(),)
        ).fetchone()
        if not team:
            raise HTTPException(status_code=400, detail="Invalid invite code — no team found with this code")
        invited_team = dict(team)

    # Check duplicate (normalized username)
    existing = conn.execute(
        "SELECT id FROM users WHERE LOWER(username) = ?", (username,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    totp_secret = pyotp.random_base32()
    totp = pyotp.TOTP(totp_secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name="Truffle AI")
    password_hash = _hash_password(req.password)

    cursor = conn.execute(
        "INSERT INTO users (username, email, totp_secret, password_hash, display_name, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, email, totp_secret, password_hash, username, now, now),
    )
    user_id = cursor.lastrowid

    # Auto-join team if invited
    if invited_team:
        conn.execute(
            "INSERT OR IGNORE INTO team_members (team_id, user_id, role) VALUES (?, ?, 'member')",
            (invited_team["id"], user_id),
        )
        log.info("User '%s' auto-joined team '%s' via invite code", username, invited_team["name"])

    conn.commit()

    # If SMTP is configured, suggest email verification
    suggest_verify = bool(os.getenv("SMTP_HOST", "").strip())

    return {
        "status": "ok",
        "message": "Registration successful",
        "role": "user",
        "suggest_verify": suggest_verify,
        "totp_secret": totp_secret,
        "provisioning_uri": provisioning_uri,
    }


# ── Email verification ──────────────────────────────────────────────────────

class SendCodeRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


@router.post("/send-verification-code")
async def send_verification_code_endpoint(req: SendCodeRequest, request: Request):
    """Send a 6-digit verification code to the given email."""
    email_error = _validate_email(req.email)
    if email_error:
        raise HTTPException(status_code=400, detail=email_error)
    email = req.email.strip().lower()

    conn = _get_conn()

    # Check cooldown
    recent = conn.execute(
        "SELECT created_at FROM verification_codes WHERE email = ? AND purpose = 'verify' AND created_at > ?",
        (email, (datetime.now(timezone.utc) - timedelta(seconds=_RESEND_COOLDOWN_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ")),
    ).fetchone()
    if recent:
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting another code")

    # Generate 6-digit code
    code = f"{secrets.randbelow(1000000):06d}"
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=_VERIFICATION_CODE_EXPIRE_MINUTES)

    # Invalidate old unused codes
    conn.execute(
        "UPDATE verification_codes SET used = 1 WHERE email = ? AND purpose = 'verify' AND used = 0",
        (email,),
    )
    conn.execute(
        "INSERT INTO verification_codes (email, code, purpose, used, expires_at, created_at) VALUES (?, ?, 'verify', 0, ?, ?)",
        (email, code, expires.strftime("%Y-%m-%dT%H:%M:%SZ"), now.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()

    sent = send_verification_code(email, code)
    if sent:
        return {"status": "ok", "message": "Verification code sent"}
    return {"status": "ok", "message": "Verification code generated (email service not configured, check server logs)"}


@router.post("/verify-email")
async def verify_email_endpoint(req: VerifyCodeRequest):
    """Verify an email with a code."""
    email = req.email.strip().lower()
    code = req.code.strip()

    conn = _get_conn()
    row = conn.execute(
        "SELECT id, code, expires_at FROM verification_codes "
        "WHERE email = ? AND purpose = 'verify' AND used = 0 ORDER BY created_at DESC LIMIT 1",
        (email,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
    if row["code"] != code:
        raise HTTPException(status_code=400, detail="Incorrect verification code")
    try:
        expires = datetime.fromisoformat(row["expires_at"])
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")

    # Mark code as used
    conn.execute("UPDATE verification_codes SET used = 1 WHERE id = ?", (row["id"],))
    # Mark user's email as verified
    conn.execute("UPDATE users SET email_verified = 1 WHERE LOWER(email) = ?", (email,))
    conn.commit()

    return {"status": "ok", "message": "Email verified successfully"}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    """Change the current user's password."""
    pw_error = _validate_password_strength(req.new_password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)
    conn = _get_conn()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    if not _verify_password(req.old_password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_hash = _hash_password(req.new_password)
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (new_hash, now, user["id"]),
    )
    conn.commit()
    return {"status": "ok", "message": "Password changed successfully"}


@router.post("/delete-account")
async def delete_account(user: dict = Depends(get_current_user)):
    """Permanently delete the current user and all associated data."""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    conn.execute("DELETE FROM settings WHERE user_id = ?", (user["id"],))
    conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    conn.commit()
    return {"status": "ok", "message": "Account permanently deleted"}


# ── OAuth connection status ─────────────────────────────────────────────────────

@router.get("/connections")
async def list_connections(user: dict = Depends(get_current_user)):
    """List connected third-party accounts (GitHub, GitLab, etc.)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT settings_json FROM settings WHERE user_id = ?", (user["id"],)
    ).fetchone()
    connections = {}
    if row:
        try:
            settings = json.loads(row["settings_json"])
            connections = settings.get("oauth_connections", {})
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "connections": [
            {"provider": "github", "connected": "github" in connections, "username": connections.get("github")},
            {"provider": "gitlab", "connected": "gitlab" in connections, "username": connections.get("gitlab")},
        ]
    }


@router.post("/connections/{provider}/disconnect")
async def disconnect_oauth(
    provider: str,
    user: dict = Depends(get_current_user),
):
    """Disconnect a third-party account."""
    if provider not in ("github", "gitlab"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    conn = _get_conn()
    row = conn.execute(
        "SELECT settings_json FROM settings WHERE user_id = ?", (user["id"],)
    ).fetchone()
    settings = {}
    if row:
        try:
            settings = json.loads(row["settings_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    connections = settings.get("oauth_connections", {})
    connections.pop(provider, None)
    settings["oauth_connections"] = connections
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO settings (user_id, settings_json, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET settings_json = ?, updated_at = ?",
        (user["id"], json.dumps(settings, ensure_ascii=False), now,
         json.dumps(settings, ensure_ascii=False), now),
    )
    conn.commit()
    return {"status": "ok", "provider": provider, "connected": False}


@router.post("/connections/{provider}/connect")
async def connect_oauth(
    provider: str,
    user: dict = Depends(get_current_user),
):
    """Simulate connecting a third-party account."""
    if provider not in ("github", "gitlab"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    conn = _get_conn()
    row = conn.execute(
        "SELECT settings_json FROM settings WHERE user_id = ?", (user["id"],)
    ).fetchone()
    settings = {}
    if row:
        try:
            settings = json.loads(row["settings_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    connections = settings.get("oauth_connections", {})
    connections[provider] = f"user_{provider}_{user['id']}"
    settings["oauth_connections"] = connections
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO settings (user_id, settings_json, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET settings_json = ?, updated_at = ?",
        (user["id"], json.dumps(settings, ensure_ascii=False), now,
         json.dumps(settings, ensure_ascii=False), now),
    )
    conn.commit()
    return {"status": "ok", "provider": provider, "connected": True, "username": connections[provider]}