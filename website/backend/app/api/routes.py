import logging

from fastapi import APIRouter, HTTPException

from app.auth.auth import get_current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "nexus-platform", "version": "2.0.0"}


@router.get("/version")
async def version():
    return {
        "project": "Truffle AI",
        "version": "2.0.0",
        "focus": "AI code generation + security scanning + expert review",
    }


@router.get("/config")
async def config():
    """Expose server-side configuration to the frontend."""
    import os
    return {
        "has_server_key": bool(os.getenv("SERVER_DEEPSEEK_KEY", "").strip()),
        "ollama_available": False,  # checked async below if needed
    }
async def system_status_endpoint():
    """Minimal system status (no longer depends on C++ engine)."""
    import os
    import platform

    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        return {
            "os": platform.system(),
            "hostname": platform.node(),
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "memory_available_mb": round(mem.available / 1024 / 1024),
        }
    except ImportError:
        return {
            "os": platform.system(),
            "hostname": platform.node(),
            "note": "Install psutil for detailed metrics",
        }
