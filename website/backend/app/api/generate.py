"""
AI code generation API — accepts idea descriptions, proxies to AI providers,
auto-scans generated code, and streams results via SSE.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()

CODE_GEN_SYSTEM_PROMPT = (
    "You are a code generation assistant. Generate clean, safe, production-ready code. "
    "Do NOT include markdown code fences. Return ONLY the code."
)


class GenerateRequest(BaseModel):
    idea: str
    language: str = "python"
    api_key: str = ""
    model: str = ""
    provider: str = ""


@router.post("/api/v1/generate/stream")
async def stream_generate(request: GenerateRequest):
    """
    Stream AI code generation with real-time token delivery via SSE.
    
    Accepts a code generation idea, proxies to the configured AI provider
    (DeepSeek, OpenAI, Anthropic, OpenRouter, or local Ollama), and streams
    the response back as SSE events. Generated code is automatically scanned
    for security issues upon completion.
    
    Events:
    - token: A code token/character
    - code_done: Full generated code
    - scan: Security scan result
    - done: Completion with task_id
    - error: Error detail
    """
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/generate/tasks")
async def list_tasks():
    """List the current user's generation tasks with pagination."""
    raise NotImplementedError("Full implementation available upon purchase")


@router.get("/api/v1/generate/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific generation task with its code and scan report."""
    raise NotImplementedError("Full implementation available upon purchase")
