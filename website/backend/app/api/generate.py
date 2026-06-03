"""
Generate API — convert natural-language idea descriptions into code
using the configured AI provider, then automatically scan for safety.

Flow:
  1. User submits an idea (text) + target language
  2. Server sends a code-generation prompt to the AI
  3. AI returns generated code
  4. Code is automatically scanned for security issues
  5. Results (code + scan report) are returned to the user
  6. Task is saved in the database for history
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request as FastAPIRequest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.db import get_conn
from app.scanner.static_analyzer import scan_code
from app.scanner.reporter import generate_report

# ── Server-side shared key (user doesn't need to configure anything) ──
SERVER_DEEPSEEK_KEY = os.getenv("SERVER_DEEPSEEK_KEY", "")
SERVER_DEFAULT_MODEL = os.getenv("SERVER_DEFAULT_MODEL", "deepseek-chat")


log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/generate")

# ── System prompt for code generation ────────────────────────────────────────

CODE_GEN_SYSTEM_PROMPT = """You are a code generator. Your job is to take a user's idea description and generate clean, working code.

Rules:
1. Generate ONLY the code, no explanations before or after.
2. Use best practices for the target language.
3. Include comments in the code to explain what each section does.
4. Do NOT include any markdown formatting like ```python or ```.
5. The code should be complete and runnable.
6. If the idea is too complex, generate a working prototype/skeleton.
7. Never include hardcoded passwords, API keys, or secrets.
8. Use safe coding practices — parameterized queries, input validation, etc.
9. For web apps, include basic HTML/CSS if needed.
10. Keep it reasonable — generate what one person can build."""


class GenerateRequest(BaseModel):
    idea: str
    language: str = "python"
    model: str = "gpt-4o"
    provider: str = "OpenAI"
    api_key: str = ""


class GenerateResponse(BaseModel):
    task_id: str
    status: str
    idea: str
    language: str
    code: str = ""
    scan_result: Optional[dict] = None


@router.post("", response_model=GenerateResponse)
async def generate_code(
    req: GenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Generate code from a natural-language idea description."""
    if not req.idea.strip():
        raise HTTPException(status_code=400, detail="Idea description cannot be empty")

    # Auto-resolve provider if no API key provided
    resolved_provider, resolved_key, resolved_model = _resolve_auto_config(
        req.provider, req.api_key, req.model
    )
    if resolved_provider == "auto":
        if await _is_ollama_running():
            resolved_provider, resolved_key, resolved_model = "Ollama", "", "qwen2.5-coder:7b"
            log.info("Auto-detected Ollama — using local generation")
        elif SERVER_DEEPSEEK_KEY:
            resolved_provider, resolved_key, resolved_model = "DeepSeek", SERVER_DEEPSEEK_KEY, SERVER_DEFAULT_MODEL
            log.info("No Ollama found — using server DeepSeek key")
        else:
            raise HTTPException(
                status_code=400,
                detail="No API key configured, Ollama not running, and no server key set. "
                       "Set SERVER_DEEPSEEK_KEY in .env or start Ollama locally.",
            )

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Save task
    conn = get_conn()
    conn.execute(
        "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'generating', ?, ?)",
        (task_id, user["id"], req.idea, req.language, now, now),
    )
    conn.commit()

    try:
        # Call AI to generate code via direct HTTP
        messages = [
            {"role": "system", "content": CODE_GEN_SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate {req.language} code for this idea:\n\n{req.idea}"},
        ]

        content = await _call_ai_provider(
            provider=resolved_provider,
            api_key=resolved_key,
            model=resolved_model,
            messages=messages,
            max_tokens=4096,
        )

        # Clean up the response - remove markdown code fences if present
        code = _clean_code_block(content, req.language)

        # Update task with generated code
        conn.execute(
            "UPDATE generation_tasks SET generated_code = ?, status = 'completed', updated_at = ? WHERE id = ?",
            (code, now, task_id),
        )
        conn.commit()

        # Auto-scan the generated code
        scan_result = scan_code(req.language, code)
        report = generate_report(scan_result)

        # Save scan result
        scan_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO scan_results (id, task_id, overall_score, summary, simple_summary, verdict, verdict_label, report_json, findings_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scan_id, task_id,
                report["score"], report["summary"], report["simple_summary"],
                report["verdict"], report["verdict_label"],
                json.dumps(report), json.dumps([f.to_dict() for f in scan_result.findings]),
                now,
            ),
        )
        conn.commit()

        log.info("Generated code for task %s (score=%d, findings=%d)",
                  task_id, report["score"], len(scan_result.findings))

        return GenerateResponse(
            task_id=task_id,
            status="completed",
            idea=req.idea,
            language=req.language,
            code=code,
            scan_result=report,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("Code generation failed: %s", e)
        conn.execute(
            "UPDATE generation_tasks SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
            (str(e), now, task_id),
        )
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


# ── Streaming generation (SSE) ────────────────────────────────────────────────

@router.post("/stream")
async def generate_code_stream(
    req: GenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Generate code with SSE streaming — tokens arrive in real-time."""
    if not req.idea.strip():
        raise HTTPException(status_code=400, detail="Idea description cannot be empty")

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_conn()
    conn.execute(
        "INSERT INTO generation_tasks (id, user_id, idea_text, language, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'generating', ?, ?)",
        (task_id, user["id"], req.idea, req.language, now, now),
    )
    conn.commit()

    messages = [
        {"role": "system", "content": CODE_GEN_SYSTEM_PROMPT},
        {"role": "user", "content": f"Generate {req.language} code for this idea:\n\n{req.idea}"},
    ]

    # Auto-resolve provider if no API key provided (resolve before streaming starts)
    stream_provider = req.provider
    stream_api_key = req.api_key
    stream_model = req.model
    if not stream_api_key:
        resolved_p, resolved_k, resolved_m = _resolve_auto_config(stream_provider, stream_api_key, stream_model)
        if resolved_p == "auto":
            if await _is_ollama_running():
                stream_provider, stream_api_key, stream_model = "Ollama", "", "qwen2.5-coder:7b"
                log.info("Auto-detected Ollama — using local generation (stream)")
            elif SERVER_DEEPSEEK_KEY:
                stream_provider, stream_api_key, stream_model = "DeepSeek", SERVER_DEEPSEEK_KEY, SERVER_DEFAULT_MODEL
                log.info("No Ollama found — using server DeepSeek key (stream)")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No API key configured, Ollama not running, and no server key set. "
                           "Set SERVER_DEEPSEEK_KEY in .env or start Ollama locally.",
                )
        else:
            stream_provider, stream_api_key, stream_model = resolved_p, resolved_k, resolved_m

    async def event_stream():
        full_code = ""
        try:
            provider = stream_provider
            api_key = stream_api_key
            model = stream_model

            PROVIDER_URLS = {
                "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
                "DeepSeek": "https://api.deepseek.com/v1/chat/completions",
                "OpenAI": "https://api.openai.com/v1/chat/completions",
                "Ollama": "http://localhost:11434/v1/chat/completions",
            }

            url = PROVIDER_URLS.get(provider)
            if not url:
                yield f"data: {json.dumps({'type': 'error', 'detail': f'Unknown provider: {provider}'})}\n\n"
                return

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            body = {
                "model": model,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.3,
                "stream": True,
            }

            if provider == "OpenRouter":
                headers["HTTP-Referer"] = "http://localhost:5173"
                headers["X-Title"] = "Truffle AI"

            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        yield f"data: {json.dumps({'type': 'error', 'detail': f'AI provider {resp.status_code}: {error_body.decode()[:300]}'})}\n\n"
                        return

                    # Stream tokens
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            payload = line[6:]
                            if payload.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(payload)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_code += content
                                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                            except json.JSONDecodeError:
                                continue

            # Stream finished — clean up and scan
            code = _clean_code_block(full_code, req.language)
            now_finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Update task in DB
            conn.execute(
                "UPDATE generation_tasks SET generated_code = ?, status = 'completed', updated_at = ? WHERE id = ?",
                (code, now_finished, task_id),
            )
            conn.commit()

            # Send code-complete event before scanning
            yield f"data: {json.dumps({'type': 'code_done', 'code': code})}\n\n"

            # Auto-scan
            scan_result = scan_code(req.language, code)
            report = generate_report(scan_result)

            scan_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO scan_results (id, task_id, overall_score, summary, simple_summary, verdict, verdict_label, report_json, findings_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (scan_id, task_id, report["score"], report["summary"], report["simple_summary"],
                 report["verdict"], report["verdict_label"], json.dumps(report),
                 json.dumps([f.to_dict() for f in scan_result.findings]), now_finished),
            )
            conn.commit()

            yield f"data: {json.dumps({'type': 'scan', 'scan_result': report})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'task_id': task_id})}\n\n"

        except Exception as e:
            log.error("Streaming generate failed: %s", e)
            conn.execute(
                "UPDATE generation_tasks SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                (str(e), now, task_id),
            )
            conn.commit()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/tasks")
async def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """List the current user's generation tasks."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, idea_text, language, status, created_at, updated_at "
        "FROM generation_tasks WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user["id"], limit, offset),
    ).fetchall()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "idea": row["idea_text"],
            "language": row["language"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    count = conn.execute(
        "SELECT COUNT(*) as c FROM generation_tasks WHERE user_id = ?",
        (user["id"],),
    ).fetchone()["c"]

    return {"tasks": tasks, "total": count}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a specific generation task with its code and scan results."""
    conn = get_conn()
    task = conn.execute(
        "SELECT * FROM generation_tasks WHERE id = ? AND user_id = ?",
        (task_id, user["id"]),
    ).fetchone()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    scan = conn.execute(
        "SELECT * FROM scan_results WHERE task_id = ?",
        (task_id,),
    ).fetchone()

    result = {
        "id": task["id"],
        "idea": task["idea_text"],
        "language": task["language"],
        "code": task["generated_code"],
        "status": task["status"],
        "error_message": task["error_message"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
    }

    if scan:
        try:
            result["scan_report"] = json.loads(scan["report_json"])
        except (json.JSONDecodeError, TypeError):
            result["scan_report"] = None
    else:
        result["scan_report"] = None

    return result


async def _is_ollama_running() -> bool:
    """Quick check if Ollama is available on localhost:11434."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _resolve_auto_config(provider: str, api_key: str, model: str) -> tuple[str, str, str]:
    """
    Resolve provider/api_key/model when user didn't provide one.
    Priority: Ollama (local) → Server DeepSeek Key.
    """
    if api_key:
        return provider, api_key, model  # user provided everything

    # Provider explicitly set to Ollama but no key needed
    if provider.lower() == "ollama":
        return "Ollama", "ollama", model or "qwen2.5-coder:7b"

    # Auto mode — resolved at call time via _is_ollama_running()
    return "auto", "", model or SERVER_DEFAULT_MODEL


async def _call_ai_provider(
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 4096,
) -> str:
    """Call the specified AI provider and return the text response."""
    # Safety fallback: if "auto" leaks through, resolve it here
    if provider == "auto":
        if await _is_ollama_running():
            provider, api_key, model = "Ollama", "", model or "qwen2.5-coder:7b"
        elif SERVER_DEEPSEEK_KEY:
            provider, api_key, model = "DeepSeek", SERVER_DEEPSEEK_KEY, model or SERVER_DEFAULT_MODEL
        else:
            raise HTTPException(status_code=400, detail="No AI provider available (Ollama offline, no server key)")

    PROVIDER_URLS: dict[str, str] = {
        "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
        "DeepSeek": "https://api.deepseek.com/v1/chat/completions",
        "OpenAI": "https://api.openai.com/v1/chat/completions",
        "Anthropic": "https://api.anthropic.com/v1/messages",
        "Ollama": "http://localhost:11434/v1/chat/completions",
    }

    # Determine URL
    if provider in PROVIDER_URLS:
        url = PROVIDER_URLS[provider]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    headers = {
        "Content-Type": "application/json",
    }

    if provider == "Anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        # Build Anthropic-format body
        system_prompt = None
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        body = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            body["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                return content
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="AI provider timeout")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail=f"AI provider error: {exc.response.text[:500]}")

    # OpenAI-compatible providers
    headers["Authorization"] = f"Bearer {api_key}"
    if provider == "OpenRouter":
        headers["HTTP-Referer"] = "http://localhost:5173"
        headers["X-Title"] = "Truffle AI"

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI provider timeout")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc.response.text[:500]}")


def _clean_code_block(code: str, language: str) -> str:
    """Remove markdown code fences from AI output."""
    # Remove leading/trailing whitespace
    code = code.strip()

    # Remove markdown code block fences
    lang_map = {"python": "python", "python3": "python", "javascript": "javascript",
                "js": "javascript", "go": "go", "cpp": "cpp", "c++": "cpp"}
    ext = lang_map.get(language, "")

    fences = [f"```{ext}", f"```{language}", "```python", "```javascript",
              "```js", "```go", "```cpp", "```c++", "```"]

    for fence in fences:
        if code.startswith(fence):
            code = code[len(fence):].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

    return code
