"""
Email utilities for sending verification codes via SMTP.

Reads SMTP configuration from environment variables and sends
HTML-formatted emails with 6-digit verification codes.
"""

import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")


def send_verification_code(to_email: str, code: str) -> bool:
    """
    Send a 6-digit verification code to the specified email address.
    
    Args:
        to_email: Recipient email address
        code: 6-digit verification code
    
    Returns:
        True if sent successfully, False otherwise
    """
    raise NotImplementedError("Full implementation available upon purchase")


def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Send an HTML email via SMTP with STARTTLS.
    
    Falls back to console logging in development mode if SMTP is not configured.
    """
    raise NotImplementedError("Full implementation available upon purchase")
