"""Expert human code review API (user-facing)."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SubmitReviewRequest(BaseModel):
    task_id: str
    notes: str = ""


@router.post("/api/v1/review/submit")
async def submit_review(request: SubmitReviewRequest):
    """
    Submit a generation task for human expert review.
    
    If Stripe is configured, the review will start in "pending_payment"
    status until payment is completed. Otherwise, it goes directly to "pending".
    """
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/review/my-requests")
async def my_review_requests():
    """List the current user's review requests with code, scan report, and admin feedback."""
    raise NotImplementedError("Full implementation available upon purchase")
