"""
Email utilities — send verification codes via SMTP.

Configure via .env:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your@email.com
  SMTP_PASS=your-app-password  (Gmail: use App Password)
  SMTP_FROM=your@email.com

If SMTP is not configured, codes are logged to console (dev mode).
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def _smtp_config() -> dict | None:
    """Read SMTP config from env. Returns None if not configured."""
    host = os.getenv("SMTP_HOST", "").strip()
    port = os.getenv("SMTP_PORT", "587").strip()
    user = os.getenv("SMTP_USER", "").strip()
    pwd = os.getenv("SMTP_PASS", "").strip()
    from_addr = os.getenv("SMTP_FROM", user).strip()
    if not host or not user or not pwd:
        return None
    return {"host": host, "port": int(port), "user": user, "password": pwd, "from": from_addr}


def send_verification_code(email: str, code: str) -> bool:
    """Send a 6-digit verification code to the given email.
    Returns True if sent, False if degraded to console log.
    """
    cfg = _smtp_config()
    subject = "TruffleKit — 邮箱验证码"
    body = f"""\
<p>您的验证码是：<strong style="font-size:24px;letter-spacing:4px">{code}</strong></p>
<p>验证码有效期为 10 分钟。如非本人操作，请忽略此邮件。</p>
<hr>
<p style="color:#888">TruffleKit — AI Code Generator</p>
"""
    if cfg:
        return _send_smtp(cfg, email, subject, body)
    # Dev mode: log instead
    log.info("📧 [DEV] Verification code for %s: %s", email, code)
    print(f"\n--- EMAIL VERIFICATION CODE ---\n  To: {email}\n  Code: {code}\n---\n", flush=True)
    return True


def _send_smtp(cfg: dict, to: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP."""
    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = to

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls(context=ctx)
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        log.info("Verification email sent to %s via %s", to, cfg["host"])
        return True
    except Exception as e:
        log.error("Failed to send email to %s: %s", to, e)
        return False
