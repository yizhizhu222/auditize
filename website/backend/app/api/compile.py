"""
Code Playground API — compile and run code in a sandboxed subprocess.

Supported languages:
  - cpp (C++20)
  - python3
  - go
  - javascript (Node.js)

Security: code is written to a temp file, compiled/run with a 10-second
timeout. For true multi-tenant isolation a container sandbox is needed.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.auth import get_current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/compile")

# ── Find binary helper ────────────────────────────────────────────────────────
def _find_binary(name: str) -> str:
    """Find a binary in common locations, falling back to PATH lookup."""
    user_bin = Path.home() / ".local" / "bin" / name
    if user_bin.is_file():
        return str(user_bin)
    tmp_go = Path("/tmp/go/bin") / name
    if tmp_go.is_file():
        return str(tmp_go)
    return name


# ── Language config ──────────────────────────────────────────────────────────
COMPILERS = {
    "cpp": {
        "ext": ".cpp",
        "compile": [_find_binary("g++"), "-std=c++20", "-O2", "-o", "{exe}", "{src}"],
        "run": ["{exe}"],
        "cleanup": True,
    },
    "python3": {
        "ext": ".py",
        "compile": None,
        "run": [_find_binary("python3"), "{src}"],
        "cleanup": False,
    },
    "go": {
        "ext": ".go",
        "compile": [_find_binary("go"), "build", "-o", "{exe}", "{src}"],
        "run": ["{exe}"],
        "cleanup": True,
    },
    "javascript": {
        "ext": ".js",
        "compile": None,
        "run": [_find_binary("node"), "{src}"],
        "cleanup": False,
    },
}

TIMEOUT = 15  # seconds


class CompileRequest(BaseModel):
    language: str = "cpp"
    code: str
    stdin: str = ""


class CompileResponse(BaseModel):
    status: str  # "ok" | "error" | "timeout" | "compile_error"
    stdout: str
    stderr: str
    elapsed_ms: int
    exit_code: int


@router.post("", response_model=CompileResponse)
async def compile_and_run(req: CompileRequest, user: dict = Depends(get_current_user)):
    if req.language not in COMPILERS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {req.language}")
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code is empty")

    config = COMPILERS[req.language]
    ext = config["ext"]

    # Write code to temp file
    tmp = tempfile.mkdtemp(prefix="playground_")
    src_path = Path(tmp) / f"code{ext}"
    exe_path = Path(tmp) / "output"

    try:
        src_path.write_text(req.code, encoding="utf-8")

        t0 = time.monotonic()

        # Compile step (if needed)
        if config["compile"]:
            compile_cmd = [part.format(exe=str(exe_path), src=str(src_path)) for part in config["compile"]]
            try:
                comp = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT,
                    cwd=tmp,
                )
            except subprocess.TimeoutExpired:
                elapsed = int((time.monotonic() - t0) * 1000)
                return CompileResponse(
                    status="timeout", stdout="", stderr="Compilation timed out",
                    elapsed_ms=elapsed, exit_code=-1,
                )

            if comp.returncode != 0:
                elapsed = int((time.monotonic() - t0) * 1000)
                return CompileResponse(
                    status="compile_error", stdout=comp.stdout, stderr=comp.stderr,
                    elapsed_ms=elapsed, exit_code=comp.returncode,
                )

        # Run step
        run_cmd = [part.format(exe=str(exe_path), src=str(src_path)) for part in config["run"]]
        try:
            proc = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                cwd=tmp,
                input=req.stdin if req.stdin else None,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - t0) * 1000)
            return CompileResponse(
                status="timeout", stdout="", stderr="Execution timed out (max 15s)",
                elapsed_ms=elapsed, exit_code=-1,
            )

        elapsed = int((time.monotonic() - t0) * 1000)
        return CompileResponse(
            status="ok",
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed_ms=elapsed,
            exit_code=proc.returncode,
        )

    except Exception as exc:
        log.error("compile error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        # Cleanup temp files
        import shutil
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
