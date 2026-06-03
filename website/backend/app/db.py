"""
Unified database init for Nexus AI v2 modules.
Tables: generation_tasks, scan_results, code_assets, review_requests,
        teams, team_members, feature_requests,
        users, sessions, settings (migrated from auth.db),
        chat_sessions, chat_messages, shared_conversations (migrated from chat_history.db).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path

log = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "app.db"
LEGACY_AUTH_DB = DB_DIR / "auth.db"
LEGACY_CHAT_DB = DB_DIR / "chat_history.db"

_LOCAL = threading.local()


def get_conn() -> sqlite3.Connection:
    """Get thread-local connection to app.db."""
    conn = getattr(_LOCAL, "app_conn", None)
    if conn is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
        conn.execute("PRAGMA foreign_keys=ON")
        _LOCAL.app_conn = conn
    return conn


def init_app_db():
    """Create all v2 tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS generation_tasks (
            id              TEXT PRIMARY KEY,
            user_id         INTEGER NOT NULL,
            idea_text       TEXT NOT NULL,
            language        TEXT NOT NULL DEFAULT 'python',
            generated_code  TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            model_used      TEXT DEFAULT '',
            error_message   TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scan_results (
            id              TEXT PRIMARY KEY,
            task_id         TEXT NOT NULL,
            overall_score   INTEGER NOT NULL DEFAULT 0,
            summary         TEXT DEFAULT '',
            simple_summary  TEXT DEFAULT '',
            verdict         TEXT DEFAULT 'unknown',
            verdict_label   TEXT DEFAULT '',
            report_json     TEXT DEFAULT '{}',
            findings_json   TEXT DEFAULT '[]',
            created_at      TEXT NOT NULL
            -- Note: no FK constraint — scan_results can be ad-hoc (no associated task)
        );

        CREATE TABLE IF NOT EXISTS code_assets (
            id              TEXT PRIMARY KEY,
            user_id         INTEGER NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            language        TEXT NOT NULL,
            code_hash       TEXT NOT NULL,
            source_task_id  TEXT,
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_requests (
            id              TEXT PRIMARY KEY,
            user_id         INTEGER NOT NULL,
            task_id         TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            notes           TEXT DEFAULT '',
            assigned_to     INTEGER,
            admin_feedback  TEXT DEFAULT '',
            admin_verdict   TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES generation_tasks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_user ON generation_tasks(user_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON generation_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_assets_user ON code_assets(user_id);
        CREATE INDEX IF NOT EXISTS idx_assets_hash ON code_assets(code_hash);
        CREATE INDEX IF NOT EXISTS idx_reviews_user ON review_requests(user_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_status ON review_requests(status);
        CREATE INDEX IF NOT EXISTS idx_scan_task ON scan_results(task_id);

        -- ── v2.1: Team collaboration ──────────────────────────────────────
        CREATE TABLE IF NOT EXISTS teams (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            invite_code     TEXT NOT NULL UNIQUE,
            created_by      INTEGER NOT NULL,
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS team_members (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            role    TEXT NOT NULL DEFAULT 'member',
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS feature_requests (
            id              TEXT PRIMARY KEY,
            team_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            linked_task_id  TEXT,
            duplicate_of    TEXT,
            reviewer_notes  TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        -- Add team_id to code_assets if not present (ALTER TABLE is additive)
        CREATE INDEX IF NOT EXISTS idx_teams_invite ON teams(invite_code);
        CREATE INDEX IF NOT EXISTS idx_members_user ON team_members(user_id);
        CREATE INDEX IF NOT EXISTS idx_members_team ON team_members(team_id);
        CREATE INDEX IF NOT EXISTS idx_requests_team ON feature_requests(team_id);
        CREATE INDEX IF NOT EXISTS idx_requests_status ON feature_requests(status);
    """)
    try:
        conn.execute("ALTER TABLE code_assets ADD COLUMN team_id TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    log.info("app.db initialized — v2.1 tables ready")

    # ── v2.2: Auth tables (migrated from auth.db) ──────────────────────────
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT NOT NULL UNIQUE,
            email        TEXT DEFAULT '',
            totp_secret  TEXT NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            display_name TEXT DEFAULT '',
            avatar_url   TEXT DEFAULT '',
            role         TEXT NOT NULL DEFAULT 'user',
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            token_jti   TEXT NOT NULL UNIQUE,
            device_info TEXT DEFAULT '',
            ip_address  TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            user_id       INTEGER PRIMARY KEY REFERENCES users(id),
            settings_json TEXT NOT NULL DEFAULT '{}',
            updated_at    TEXT NOT NULL
        );
    """)

    # ── v2.3: Chat tables (migrated from chat_history.db) ──────────────────
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL DEFAULT '新对话',
            user_id    INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS shared_conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL DEFAULT '共享对话',
            session_id  INTEGER NOT NULL,
            shared_by   TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_shared_created ON shared_conversations(created_at DESC);
    """)
    conn.commit()
    log.info("Unified DB: auth + chat tables ready")

    # ── v2.5: Notifications table ──────────────────────────────────────────
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            type        TEXT NOT NULL DEFAULT 'info',
            title       TEXT NOT NULL,
            message     TEXT DEFAULT '',
            related_id  TEXT DEFAULT '',
            is_read     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);
    """)
    conn.commit()
    log.info("Unified DB: notifications table ready")

    # ── v2.7: Verification codes + login attempts ──────────────────────────
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS verification_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT NOT NULL,
            code        TEXT NOT NULL,
            purpose     TEXT NOT NULL DEFAULT 'register',
            used        INTEGER NOT NULL DEFAULT 0,
            expires_at  TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vcode_email ON verification_codes(email, purpose, used);

        CREATE TABLE IF NOT EXISTS login_attempts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            ip_address  TEXT DEFAULT '',
            success     INTEGER NOT NULL DEFAULT 0,
            attempted_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_login_user ON login_attempts(username, attempted_at);
    """)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    log.info("Unified DB: verification + lockout tables ready")


def migrate_from_legacy():
    """Copy data from legacy auth.db / chat_history.db into app.db (idempotent)."""
    unified = get_conn()

    # Sentinel row: user_id=0, settings_json='{"migrated":true}' marks completion
    sentinel = unified.execute(
        "SELECT 1 FROM settings WHERE user_id = 0 AND settings_json = '{\"migrated\":true}'"
    ).fetchone()
    if sentinel:
        log.info("Legacy migration already completed, skipping")
        return

    # ── Migrate auth.db ──
    if LEGACY_AUTH_DB.exists():
        try:
            legacy = sqlite3.connect(str(LEGACY_AUTH_DB))
            legacy.row_factory = sqlite3.Row
            log.info("Migrating data from auth.db ...")

            cols = [r[1] for r in legacy.execute("PRAGMA table_info(users)")]
            has_password = "password_hash" in cols
            has_role = "role" in cols

            rows = [dict(r) for r in legacy.execute("SELECT * FROM users").fetchall()]
            for r in rows:
                pw = r["password_hash"] if has_password else ""
                role = r["role"] if has_role else "user"
                try:
                    unified.execute(
                        "INSERT OR IGNORE INTO users (id,username,email,totp_secret,password_hash,display_name,avatar_url,role,created_at,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (r["id"], r["username"], r["email"], r["totp_secret"], pw,
                         r.get("display_name", "") or "", r.get("avatar_url", "") or "",
                         role, r["created_at"], r["updated_at"]),
                    )
                except sqlite3.IntegrityError:
                    pass

            sess_rows = [dict(s) for s in legacy.execute("SELECT * FROM sessions").fetchall()]
            for s in sess_rows:
                try:
                    unified.execute(
                        "INSERT OR IGNORE INTO sessions (id,user_id,token_jti,device_info,ip_address,created_at,expires_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (s["id"], s["user_id"], s["token_jti"], s.get("device_info", "") or "",
                         s.get("ip_address", "") or "", s["created_at"], s["expires_at"]),
                    )
                except sqlite3.IntegrityError:
                    pass

            settings_rows = [dict(s) for s in legacy.execute("SELECT * FROM settings").fetchall()]
            for s in settings_rows:
                try:
                    unified.execute(
                        "INSERT OR IGNORE INTO settings (user_id,settings_json,updated_at) VALUES (?,?,?)",
                        (s["user_id"], s.get("settings_json", "{}") or "{}", s["updated_at"]),
                    )
                except sqlite3.IntegrityError:
                    pass

            legacy.close()
            log.info("Migrated %d users, %d sessions, %d settings from auth.db",
                      len(rows), len(sess_rows), len(settings_rows))
        except Exception as e:
            log.warning("Legacy auth.db migration error (non-fatal): %s", e)

    # ── Migrate chat_history.db ──
    if LEGACY_CHAT_DB.exists():
        try:
            legacy = sqlite3.connect(str(LEGACY_CHAT_DB))
            legacy.row_factory = sqlite3.Row
            log.info("Migrating data from chat_history.db ...")

            chat_sess = [dict(s) for s in legacy.execute("SELECT * FROM chat_sessions").fetchall()]
            for s in chat_sess:
                try:
                    unified.execute(
                        "INSERT OR IGNORE INTO chat_sessions (id,title,user_id,created_at,updated_at) VALUES (?,?,?,?,?)",
                        (s["id"], s["title"], s["user_id"], s["created_at"], s["updated_at"]),
                    )
                except sqlite3.IntegrityError:
                    pass

            msgs = [dict(m) for m in legacy.execute("SELECT * FROM chat_messages").fetchall()]
            for m in msgs:
                try:
                    unified.execute(
                        "INSERT OR IGNORE INTO chat_messages (id,session_id,role,content,created_at) VALUES (?,?,?,?,?)",
                        (m["id"], m["session_id"], m["role"], m["content"], m["created_at"]),
                    )
                except sqlite3.IntegrityError:
                    pass

            shared = [dict(s) for s in legacy.execute("SELECT * FROM shared_conversations").fetchall()]
            for s in shared:
                try:
                    unified.execute(
                        "INSERT OR IGNORE INTO shared_conversations (id,title,session_id,shared_by,message_count,created_at) VALUES (?,?,?,?,?,?)",
                        (s["id"], s["title"], s["session_id"], s["shared_by"], s.get("message_count", 0), s["created_at"]),
                    )
                except sqlite3.IntegrityError:
                    pass

            legacy.close()
            log.info("Migrated %d chat sessions, %d messages, %d shared from chat_history.db",
                      len(chat_sess), len(msgs), len(shared))
        except Exception as e:
            log.warning("Legacy chat_history.db migration error (non-fatal): %s", e)

    # Mark migration complete
    try:
        unified.execute("PRAGMA foreign_keys=OFF")
        unified.execute(
            "INSERT OR IGNORE INTO settings (user_id,settings_json,updated_at) VALUES (0,'{\"migrated\":true}','')"
        )
    except sqlite3.IntegrityError:
        log.warning("Could not insert migration sentinel (non-fatal)")
    finally:
        unified.execute("PRAGMA foreign_keys=ON")
    unified.commit()
    log.info("Legacy data migration complete")
