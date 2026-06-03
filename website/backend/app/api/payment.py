"""
Payment API — Stripe Checkout integration for expert review.

Prerequisites (set in .env):
  STRIPE_SECRET_KEY=sk_live_...
  STRIPE_PUBLISHABLE_KEY=pk_live_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  PAYMENT_PRICE_USD=999        # price per review in cents ($9.99)
  SITE_URL=https://trufflekit.com   # defaults to localhost for dev
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.db import get_conn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payment")

STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PRICE_CENTS = int(os.getenv("PAYMENT_PRICE_USD", "999"))
SITE_URL = os.getenv("SITE_URL", "http://localhost:5173")

stripe = None
if STRIPE_API_KEY:
    import stripe as _stripe
    _stripe.api_key = STRIPE_API_KEY
    stripe = _stripe


class CreateCheckoutRequest(BaseModel):
    review_id: str


@router.post("/create-checkout-session")
async def create_checkout_session(
    req: CreateCheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for paying for a review."""
    if not stripe:
        raise HTTPException(status_code=503, detail="Payment not configured (missing STRIPE_SECRET_KEY)")

    conn = get_conn()
    review = conn.execute(
        "SELECT r.id, r.status, t.idea_text "
        "FROM review_requests r "
        "JOIN generation_tasks t ON r.task_id = t.id "
        "WHERE r.id = ? AND r.user_id = ?",
        (req.review_id, user["id"]),
    ).fetchone()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review["status"] != "pending_payment":
        raise HTTPException(status_code=409, detail=f"Review is already {review['status']}")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Expert Code Review",
                        "description": f"Review for: {review['idea_text'][:80]}",
                    },
                    "unit_amount": PRICE_CENTS,
                },
                "quantity": 1,
            }],
            metadata={"review_id": req.review_id, "user_id": str(user["id"])},
            success_url=f"{SITE_URL}/settings?review_paid={req.review_id}",
            cancel_url=f"{SITE_URL}/reviews",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        log.error("Stripe checkout session creation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook — handles checkout.session.completed events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not stripe or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Payment webhook not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        review_id = session["metadata"].get("review_id")
        user_id = session["metadata"].get("user_id")

        if review_id and user_id:
            conn = get_conn()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                "UPDATE review_requests SET status = 'pending', updated_at = ? WHERE id = ? AND status = 'pending_payment'",
                (now, review_id),
            )
            conn.commit()
            log.info("Payment completed for review %s (user %s)", review_id, user_id)

    return {"status": "ok"}


@router.get("/config")
async def payment_config():
    """Return public payment config (no secrets)."""
    return {
        "configured": bool(stripe),
        "price_cents": PRICE_CENTS,
        "price_dollars": f"${PRICE_CENTS / 100:.2f}",
    }
