"""
Comprehensive tests for Assets API: save, list, delete, check-similar.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestAssets:
    """Code asset library CRUD."""

    ASSET_CODE = "print('hello world')\n# Simple Python script"

    @pytest.mark.asyncio
    async def test_save_asset(self, client: AsyncClient, auth_headers: dict):
        """Save a code asset."""
        resp = await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "Hello World",
            "language": "python",
            "code": self.ASSET_CODE,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "asset_id" in data
        assert data["duplicate"] is False

    @pytest.mark.asyncio
    async def test_save_asset_empty_code(self, client: AsyncClient, auth_headers: dict):
        """Empty code should 400."""
        resp = await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "Empty",
            "code": "",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_save_asset_empty_title(self, client: AsyncClient, auth_headers: dict):
        """Empty title should 400."""
        resp = await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "",
            "code": "x = 1",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_save_duplicate(self, client: AsyncClient, auth_headers: dict):
        """Same code hash should be detected as duplicate."""
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "First",
            "code": "unique_code_42",
        })
        resp = await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "Second",
            "code": "unique_code_42",
        })
        assert resp.status_code == 200
        assert resp.json()["duplicate"] is True

    @pytest.mark.asyncio
    async def test_save_asset_with_team(self, client: AsyncClient, auth_headers: dict):
        """Save asset with team_id."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "AssetTeam"})).json()
        resp = await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "Team Asset",
            "language": "python",
            "code": "team_asset_code",
            "team_id": team["team_id"],
        })
        assert resp.status_code == 200
        assert resp.json()["duplicate"] is False

    @pytest.mark.asyncio
    async def test_save_asset_with_source_task(self, client: AsyncClient, auth_headers: dict):
        """Save with source_task_id."""
        resp = await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "From Task",
            "code": "from_task_code",
            "source_task_id": "task-123",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_assets(self, client: AsyncClient, auth_headers: dict):
        """List assets."""
        # Save a couple
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "ListTest1", "code": "list_test_1",
        })
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "ListTest2", "code": "list_test_2",
        })
        resp = await client.get("/api/v1/assets", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 2
        titles = [a["title"] for a in data["assets"]]
        assert "ListTest1" in titles

    @pytest.mark.asyncio
    async def test_list_assets_filter_language(self, client: AsyncClient, auth_headers: dict):
        """Filter assets by language."""
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "PyScript", "language": "python", "code": "py_code",
        })
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "JSScript", "language": "javascript", "code": "js_code",
        })
        resp = await client.get("/api/v1/assets?language=javascript", headers=auth_headers)
        assert resp.status_code == 200
        langs = set(a["language"] for a in resp.json()["assets"])
        assert langs == {"javascript"}

    @pytest.mark.asyncio
    async def test_list_assets_search(self, client: AsyncClient, auth_headers: dict):
        """Search assets by title."""
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "Inventory System", "code": "inv_code",
        })
        resp = await client.get("/api/v1/assets?search=Inventory", headers=auth_headers)
        assert resp.status_code == 200
        titles = [a["title"] for a in resp.json()["assets"]]
        assert any("Inventory" in t for t in titles)

    @pytest.mark.asyncio
    async def test_list_assets_team_filter(self, client: AsyncClient, auth_headers: dict):
        """Filter assets by team_id."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "AssetTeam2"})).json()
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "TeamAsset2", "code": "team_asset_2", "team_id": team["team_id"],
        })
        resp = await client.get(f"/api/v1/assets?team_id={team['team_id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    @pytest.mark.asyncio
    async def test_delete_asset(self, client: AsyncClient, auth_headers: dict):
        """Delete an asset."""
        saved = (await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "DeleteMe", "code": "delete_me",
        })).json()
        resp = await client.delete(f"/api/v1/assets/{saved['asset_id']}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient, auth_headers: dict):
        """Delete non-existent asset should 404."""
        resp = await client.delete("/api/v1/assets/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_check_similar(self, client: AsyncClient, auth_headers: dict):
        """Check similar assets."""
        await client.post("/api/v1/assets", headers=auth_headers, json={
            "title": "Order Management System",
            "description": "Track orders, manage inventory",
            "code": "order_system_code",
        })
        resp = await client.post("/api/v1/assets/check-similar", headers=auth_headers, json={
            "idea": "I want an order management system with inventory tracking",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "has_similar" in data
        assert "similar_assets" in data

    @pytest.mark.asyncio
    async def test_check_similar_empty(self, client: AsyncClient, auth_headers: dict):
        """Empty idea should 400."""
        resp = await client.post("/api/v1/assets/check-similar", headers=auth_headers, json={
            "idea": "",
        })
        assert resp.status_code == 400
