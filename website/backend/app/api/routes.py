"""Health check, version info, and system configuration endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/health")
async def health_check():
    """Health check endpoint returning service status and version."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/version")
async def version_info():
    """Return project version and build information."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/config")
async def server_config():
    """
    Return server-side configuration flags.
    
    Used by the frontend to determine:
    - has_server_key: Whether a shared AI API key is configured
    - ollama_available: Whether local Ollama instance is running
    """
    raise NotImplementedError("Full implementation available upon purchase")
