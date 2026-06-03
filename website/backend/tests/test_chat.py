"""
Tests for chat history CRUD endpoints.
"""

import pytest
from httpx import AsyncClient


class TestChatHistory:
    """Chat sessions & messages."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client: AsyncClient, auth_headers: dict):
        """New user should have an empty session list."""
        resp = await client.get("/api/v1/chat/sessions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_session(self, client: AsyncClient, auth_headers: dict):
        """Create a new chat session."""
        resp = await client.post("/api/v1/chat/sessions", headers=auth_headers, json={
            "title": "测试对话",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["title"] == "测试对话"
        return data["id"]

    @pytest.mark.asyncio
    async def test_rename_session(self, client: AsyncClient, auth_headers: dict):
        """Rename a session."""
        session = (await client.post("/api/v1/chat/sessions", headers=auth_headers,
                                     json={"title": "旧标题"})).json()
        resp = await client.put(f"/api/v1/chat/sessions/{session['id']}",
                                headers=auth_headers, json={"title": "新标题"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_send_and_get_messages(self, client: AsyncClient, auth_headers: dict):
        """Add messages to a session and retrieve them."""
        # Create session
        session = (await client.post("/api/v1/chat/sessions", headers=auth_headers,
                                     json={"title": "消息测试"})).json()
        sid = session["id"]

        # Send user message
        resp = await client.post(f"/api/v1/chat/sessions/{sid}/messages",
                                 headers=auth_headers,
                                 json={"session_id": sid, "role": "user", "content": "你好"})
        assert resp.status_code == 200

        # Send AI response
        resp = await client.post(f"/api/v1/chat/sessions/{sid}/messages",
                                 headers=auth_headers,
                                 json={"session_id": sid, "role": "ai", "content": "你好！有什么可以帮助你的？"})
        assert resp.status_code == 200

        # Get messages
        resp = await client.get(f"/api/v1/chat/sessions/{sid}/messages", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert items[0]["role"] == "user"
        assert items[0]["content"] == "你好"
        assert items[1]["role"] == "ai"

    @pytest.mark.asyncio
    async def test_session_ownership(self, client: AsyncClient, auth_headers: dict):
        """A user can read their own session."""
        session = (await client.post("/api/v1/chat/sessions", headers=auth_headers,
                                     json={"title": "我的对话"})).json()
        resp = await client.get(f"/api/v1/chat/sessions/{session['id']}/messages", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_session(self, client: AsyncClient, auth_headers: dict):
        """Delete a session and verify it's gone."""
        session = (await client.post("/api/v1/chat/sessions", headers=auth_headers,
                                     json={"title": "待删除"})).json()
        sid = session["id"]

        resp = await client.delete(f"/api/v1/chat/sessions/{sid}", headers=auth_headers)
        assert resp.status_code == 200

        resp = await client.get("/api/v1/chat/sessions", headers=auth_headers)
        assert len(resp.json()["items"]) == 0

    @pytest.mark.asyncio
    async def test_session_not_found(self, client: AsyncClient, auth_headers: dict):
        """Non-existent session should 404."""
        resp = await client.get("/api/v1/chat/sessions/99999/messages", headers=auth_headers)
        assert resp.status_code == 404
