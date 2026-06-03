"""
Chat — AI API proxy endpoint.

Proxies chat completion requests to the configured provider (OpenRouter, DeepSeek,
Anthropic, OpenAI, or a custom OpenAI-compatible endpoint). Supports both streaming
(SSE) and non-streaming modes.

API keys are accepted in the request body so that each request can use the key
the user has configured in their settings. JWT auth is optional.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.auth.auth import get_current_user, get_optional_user, require_admin

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat")

# ── Usage tracking (in-memory) ──────────────────────────────────────────────
_usage: dict[str, int] = {}  # "YYYY-MM-DD:user_id" → count


def record_usage(user_id: int):
    from datetime import date
    key = f"{date.today()}:{user_id}"
    _usage[key] = _usage.get(key, 0) + 1


def get_usage(days: int = 7) -> list[dict]:
    from datetime import date, timedelta
    result = []
    for i in range(days):
        d = date.today() - timedelta(days=i)
        # Aggregate across all users for that day
        total = sum(v for k, v in _usage.items() if k.startswith(f"{d}:"))
        result.append({"date": str(d), "count": total})
    return result


def get_usage_by_user() -> list[dict]:
    from datetime import date
    prefix = f"{date.today()}"
    users: dict[str, int] = {}
    for k, v in _usage.items():
        if k.startswith(prefix):
            uid = k.split(":", 1)[1]
            users[uid] = users.get(uid, 0) + v
    return [{"user_id": uid, "count": c} for uid, c in sorted(users.items(), key=lambda x: -x[1])]

# ── Provider base URLs ──────────────────────────────────────────────────────────
PROVIDER_URLS: dict[str, str] = {
    "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
    "DeepSeek": "https://api.deepseek.com/v1/chat/completions",
    "OpenAI": "https://api.openai.com/v1/chat/completions",
    "Anthropic": "https://api.anthropic.com/v1/messages",
    "Ollama": "http://localhost:11434/v1/chat/completions",
}

# ── Request / Response models ───────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # system | user | assistant
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    provider: str = "OpenRouter"
    api_key: str = ""
    base_url: Optional[str] = None  # for Custom provider
    stream: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7


class ChatResponse(BaseModel):
    model: str
    provider: str
    content: str
    usage: Optional[dict] = None


# ── Endpoint ────────────────────────────────────────────────────────────────────
@router.post("/completions")
async def chat_completions(
    req: ChatRequest,
    request: FastAPIRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    """Proxy a chat completion to the specified AI provider."""
    provider = req.provider
    api_key = req.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail=f"No API key provided for {provider}")

    # Determine the upstream URL
    if provider == "Custom" and req.base_url:
        base = req.base_url.rstrip("/")
        url = f"{base}/chat/completions" if not base.endswith("/chat/completions") else base
    elif provider in PROVIDER_URLS:
        url = PROVIDER_URLS[provider]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    if provider == "Anthropic":
        return await _proxy_anthropic(req, url)
    else:
        return await _proxy_openai_compat(req, url)


async def _proxy_openai_compat(req: ChatRequest, url: str) -> StreamingResponse | JSONResponse:
    """Proxy to an OpenAI-compatible chat completions endpoint."""
    headers = {
        "Authorization": f"Bearer {req.api_key}",
        "Content-Type": "application/json",
    }

    # Map provider-specific headers
    if req.provider == "OpenRouter":
        headers["HTTP-Referer"] = "http://localhost:5173"
        headers["X-Title"] = "Nexus AI Platform"

    body = {
        "model": req.model,
        "messages": [m.model_dump() for m in req.messages],
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "stream": req.stream,
    }

    if req.stream:
        return await _stream_openai(url, headers, body)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if user:
                record_usage(int(user["id"]))
            return JSONResponse(content={
                "model": req.model,
                "provider": req.provider,
                "content": content,
                "usage": data.get("usage"),
            })
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.HTTPStatusError as exc:
        detail = f"Upstream {exc.response.status_code}: {exc.response.text[:500]}"
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except Exception as exc:
        log.error("Chat proxy error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


async def _stream_openai(
    url: str, headers: dict, body: dict
) -> StreamingResponse:
    """Stream an OpenAI-compatible SSE response back to the client."""
    async def event_generator():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    yield f"data: {json.dumps({'error': error_body.decode()[:500]})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line + "\n"
                    elif line.startswith("data: [DONE]"):
                        yield "data: [DONE]\n\n"
                        return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


async def _proxy_anthropic(req: ChatRequest, url: str) -> StreamingResponse | JSONResponse:
    """Proxy to Anthropic's Messages API (different schema from OpenAI)."""
    headers = {
        "x-api-key": req.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    # Build Anthropic-format messages from our generic ChatMessage list
    system_prompt = None
    anthropic_messages = []
    for m in req.messages:
        if m.role == "system":
            system_prompt = m.content
        else:
            anthropic_messages.append({"role": m.role, "content": m.content})

    body: dict = {
        "model": req.model,
        "messages": anthropic_messages,
        "max_tokens": req.max_tokens,
    }
    if system_prompt:
        body["system"] = system_prompt
    if req.stream:
        body["stream"] = True

    if req.stream:
        return await _stream_anthropic(url, headers, body)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")
            return JSONResponse(content={
                "model": req.model,
                "provider": "Anthropic",
                "content": content,
                "usage": data.get("usage"),
            })
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.HTTPStatusError as exc:
        detail = f"Upstream {exc.response.status_code}: {exc.response.text[:500]}"
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except Exception as exc:
        log.error("Anthropic proxy error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


async def _stream_anthropic(
    url: str, headers: dict, body: dict
) -> StreamingResponse:
    """Stream an Anthropic SSE response back to the client."""
    async def event_generator():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    yield f"data: {json.dumps({'error': error_body.decode()[:500]})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("event: ") or line.startswith("data: "):
                        yield line + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── Test Connection ────────────────────────────────────────────────────────────

class TestConnectionRequest(BaseModel):
    provider: str
    api_key: str = ""
    base_url: Optional[str] = None


@router.post("/test-connection")
async def test_connection(
    req: TestConnectionRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    provider = req.provider
    api_key = req.api_key

    if provider == "Anthropic":
        url = "https://api.anthropic.com/v1/models"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    elif provider == "OpenRouter":
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
    elif provider == "DeepSeek":
        url = "https://api.deepseek.com/models"
        headers = {"Authorization": f"Bearer {api_key}"}
    elif provider == "OpenAI":
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
    elif provider == "Ollama":
        url = "http://localhost:11434/api/tags"
        headers = {}
    elif provider == "Custom" and req.base_url:
        base = req.base_url.rstrip("/")
        urls = [f"{base}/models", f"{base}/v1/models"]
        headers = {"Authorization": f"Bearer {api_key}"}
        return await _test_custom_endpoints(urls, headers)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            elapsed = time.monotonic() - t0
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", data.get("models", []))
                return {"status": "ok", "provider": provider,
                        "models_count": len(models) if isinstance(models, list) else 0,
                        "latency_ms": round(elapsed * 1000)}
            else:
                return {"status": "error", "provider": provider,
                        "error": f"{resp.status_code}: {resp.text[:200]}",
                        "latency_ms": round(elapsed * 1000)}
    except Exception as exc:
        elapsed = time.monotonic() - t0
        return {"status": "error", "provider": provider,
                "error": str(exc), "latency_ms": round(elapsed * 1000)}


async def _test_custom_endpoints(urls: list[str], headers: dict) -> dict:
    for url in urls:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                elapsed = time.monotonic() - t0
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", data.get("models", []))
                    return {"status": "ok", "provider": "Custom",
                            "models_count": len(models) if isinstance(models, list) else 0,
                            "latency_ms": round(elapsed * 1000)}
        except Exception:
            continue
    return {"status": "error", "provider": "Custom", "error": "No endpoint responded"}


# /usage endpoint removed in v2 — no longer needed
