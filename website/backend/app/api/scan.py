"""
Scan API — submit code for security analysis and get a human-readable report.

Two modes:
  1. POST /api/v1/scan — scan arbitrary code (paste in)
  2. GET /api/v1/scan/tasks/{task_id} — get scan results for an existing generation task
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.auth import get_current_user, get_optional_user
from app.db import get_conn
from app.scanner.static_analyzer import scan_code
from app.scanner.reporter import generate_report

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/scan")


class ScanRequest(BaseModel):
    code: str
    language: str = "python"


class ScanResponse(BaseModel):
    scan_id: str
    report: dict


@router.post("", response_model=ScanResponse)
async def scan_code_endpoint(
    req: ScanRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    """Scan arbitrary code for security issues. No generation or API key required."""
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    supported = {"python", "javascript", "go", "cpp"}
    if req.language not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {req.language}. Supported: {', '.join(sorted(supported))}")

    result = scan_code(req.language, req.code)
    report = generate_report(result)

    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Save as an ad-hoc scan if user is authenticated
    if user:
        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO scan_results (id, task_id, overall_score, summary, simple_summary, "
                "verdict, verdict_label, report_json, findings_json, created_at) "
                "VALUES (?, 'ad-hoc', ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    scan_id,
                    report["score"], report["summary"], report["simple_summary"],
                    report["verdict"], report["verdict_label"],
                    json.dumps(report), json.dumps([f.to_dict() for f in result.findings]),
                    now,
                ),
            )
            conn.commit()
        except Exception:
            pass  # Best-effort save

    log.info("Ad-hoc scan %s: score=%d, findings=%d", scan_id, report["score"], len(result.findings))

    return ScanResponse(scan_id=scan_id, report=report)


@router.get("/tasks/{task_id}")
async def get_scan_for_task(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """Get the latest scan report for a generation task."""
    conn = get_conn()
    scan = conn.execute(
        "SELECT * FROM scan_results WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
        (task_id,),
    ).fetchone()

    if not scan:
        raise HTTPException(status_code=404, detail="No scan results found for this task")

    try:
        report = json.loads(scan["report_json"])
    except (json.JSONDecodeError, TypeError):
        report = {}

    return {
        "scan_id": scan["id"],
        "task_id": scan["task_id"],
        "score": scan["overall_score"],
        "verdict": scan["verdict"],
        "created_at": scan["created_at"],
        "report": report,
    }


@router.get("/history")
async def get_scan_history(user: dict = Depends(get_current_user)):
    """Get recent scan history for the current user."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT s.id, s.task_id, s.overall_score, s.verdict, s.simple_summary, s.created_at, "
        "t.idea_text, t.language "
        "FROM scan_results s "
        "LEFT JOIN generation_tasks t ON s.task_id = t.id "
        "WHERE s.task_id != 'ad-hoc' OR (s.task_id = 'ad-hoc' AND s.id IN "
        "(SELECT s2.id FROM scan_results s2 WHERE s2.task_id = 'ad-hoc' ORDER BY s2.created_at DESC LIMIT 20)) "
        "ORDER BY s.created_at DESC LIMIT 50",
    ).fetchall()

    history = []
    for row in rows:
        history.append({
            "scan_id": row["id"],
            "task_id": row["task_id"],
            "score": row["overall_score"],
            "verdict": row["verdict"],
            "summary": row["simple_summary"],
            "idea": row["idea_text"] if row["idea_text"] else "(Pasted code)",
            "language": row["language"] if row["language"] else "unknown",
            "scanned_at": row["created_at"],
        })

    return {"history": history}
