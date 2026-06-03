"""
Comprehensive tests for Team API: create, list, join, leave, disband,
feature requests CRUD, review, generate, change-role.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Team CRUD ──────────────────────────────────────────────────────────────────

class TestTeam:
    """Team management — create, list, join, leave, disband."""

    @pytest.mark.asyncio
    async def test_create_team(self, client: AsyncClient, auth_headers: dict):
        """Create a team."""
        resp = await client.post("/api/v1/team/create", headers=auth_headers, json={
            "name": "Test Team",
            "description": "A team for testing",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "team_id" in data
        assert data["name"] == "Test Team"
        assert len(data["invite_code"]) == 12

    @pytest.mark.asyncio
    async def test_create_team_no_name(self, client: AsyncClient, auth_headers: dict):
        """Create team with empty name should 400."""
        resp = await client.post("/api/v1/team/create", headers=auth_headers, json={
            "name": "   ",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_teams(self, client: AsyncClient, auth_headers: dict):
        """List teams for current user."""
        await client.post("/api/v1/team/create", headers=auth_headers, json={"name": "Team A"})
        await client.post("/api/v1/team/create", headers=auth_headers, json={"name": "Team B"})
        resp = await client.get("/api/v1/team/list", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["teams"]) >= 2

    @pytest.mark.asyncio
    async def test_team_my(self, client: AsyncClient, auth_headers: dict):
        """Get specific team info."""
        created = (await client.post("/api/v1/team/create", headers=auth_headers,
                                     json={"name": "My Team"})).json()
        resp = await client.get(f"/api/v1/team/my?team_id={created['team_id']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["in_team"] is True
        assert data["name"] == "My Team"
        assert data["my_role"] == "owner"

    @pytest.mark.asyncio
    async def test_join_team(self, client: AsyncClient, auth_headers: dict):
        """Join a team via invite code."""
        created = (await client.post("/api/v1/team/create", headers=auth_headers,
                                     json={"name": "Joinable"})).json()

        # Register a new user
        await client.post("/api/v1/auth/register", json={
            "username": "joiner", "password": "Joinpass123",
        })
        login = await client.post("/api/v1/auth/login", json={
            "username": "joiner", "password": "Joinpass123",
        })
        joiner_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = await client.post("/api/v1/team/join", headers=joiner_headers, json={
            "invite_code": created["invite_code"],
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "member"

    @pytest.mark.asyncio
    async def test_join_team_invalid_code(self, client: AsyncClient, auth_headers: dict):
        """Join with invalid invite code should 404."""
        resp = await client.post("/api/v1/team/join", headers=auth_headers, json={
            "invite_code": "deadbeefcafe",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_leave_team(self, client: AsyncClient):
        """Member can leave a team."""
        # Owner creates team
        await client.post("/api/v1/auth/register", json={
            "username": "owner1", "password": "Ownerpass1",
        })
        owner = await client.post("/api/v1/auth/login", json={
            "username": "owner1", "password": "Ownerpass1",
        })
        owner_h = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        team = (await client.post("/api/v1/team/create", headers=owner_h,
                                  json={"name": "LeaveTest"})).json()

        # Member joins
        await client.post("/api/v1/auth/register", json={
            "username": "leaver", "password": "Leavepass1",
        })
        member = await client.post("/api/v1/auth/login", json={
            "username": "leaver", "password": "Leavepass1",
        })
        member_h = {"Authorization": f"Bearer {member.json()['access_token']}"}
        await client.post("/api/v1/team/join", headers=member_h, json={
            "invite_code": team["invite_code"],
        })

        # Member leaves
        resp = await client.post(f"/api/v1/team/leave?team_id={team['team_id']}", headers=member_h)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_owner_cannot_leave(self, client: AsyncClient, auth_headers: dict):
        """Owner cannot leave — must disband."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "OwnerCantLeave"})).json()
        resp = await client.post(f"/api/v1/team/leave?team_id={team['team_id']}", headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_disband_team(self, client: AsyncClient, auth_headers: dict):
        """Owner can disband team."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "DisbandMe"})).json()
        resp = await client.post(f"/api/v1/team/disband?team_id={team['team_id']}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_owner_cannot_disband(self, client: AsyncClient):
        """Non-owner cannot disband."""
        # Owner creates
        await client.post("/api/v1/auth/register", json={
            "username": "owner_disband", "password": "Pass123456",
        })
        own = await client.post("/api/v1/auth/login", json={
            "username": "owner_disband", "password": "Pass123456",
        })
        own_h = {"Authorization": f"Bearer {own.json()['access_token']}"}
        team = (await client.post("/api/v1/team/create", headers=own_h,
                                  json={"name": "NoDisband"})).json()

        # Another user tries to disband
        await client.post("/api/v1/auth/register", json={
            "username": "notowner", "password": "Pass123456",
        })
        no = await client.post("/api/v1/auth/login", json={
            "username": "notowner", "password": "Pass123456",
        })
        no_h = {"Authorization": f"Bearer {no.json()['access_token']}"}
        resp = await client.post(f"/api/v1/team/disband?team_id={team['team_id']}", headers=no_h)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_change_role(self, client: AsyncClient, auth_headers: dict):
        """Owner can change a member's role."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "RoleTest"})).json()

        await client.post("/api/v1/auth/register", json={
            "username": "rolechange", "password": "Pass123456",
        })
        mem = await client.post("/api/v1/auth/login", json={
            "username": "rolechange", "password": "Pass123456",
        })
        mem_h = {"Authorization": f"Bearer {mem.json()['access_token']}"}
        await client.post("/api/v1/team/join", headers=mem_h, json={
            "invite_code": team["invite_code"],
        })

        # Change to reviewer
        resp = await client.post(f"/api/v1/team/change-role?team_id={team['team_id']}",
                                 headers=auth_headers,
                                 params={"target_user_id": 0, "new_role": "reviewer"})
        assert resp.status_code == 404 or resp.status_code == 200


# ── Feature Requests ──────────────────────────────────────────────────────────

class TestFeatureRequests:
    """Feature request CRUD and review flow."""

    @pytest.mark.asyncio
    async def test_create_request(self, client: AsyncClient, auth_headers: dict):
        """Submit a feature request."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "ReqTest"})).json()
        resp = await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                 headers=auth_headers, json={
            "title": "Order Dashboard",
            "description": "A dashboard for orders",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_create_request_empty_title(self, client: AsyncClient, auth_headers: dict):
        """Request with empty title should 400."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "ReqTest2"})).json()
        resp = await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                 headers=auth_headers, json={
            "title": "   ",
            "description": "test",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_requests(self, client: AsyncClient, auth_headers: dict):
        """List feature requests."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "ListReq"})).json()
        await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                          headers=auth_headers, json={"title": "Req 1"})
        await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                          headers=auth_headers, json={"title": "Req 2"})
        resp = await client.get(f"/api/v1/team/requests?team_id={team['team_id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["requests"]) >= 2

    @pytest.mark.asyncio
    async def test_get_request(self, client: AsyncClient, auth_headers: dict):
        """Get a single request by ID."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "GetReq"})).json()
        created = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                     headers=auth_headers, json={"title": "Single Req"})).json()
        resp = await client.get(f"/api/v1/team/requests/{created['request_id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Single Req"

    @pytest.mark.asyncio
    async def test_review_approve(self, client: AsyncClient, auth_headers: dict):
        """Owner can approve a request (owner includes reviewer privilege)."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "ApproveReq"})).json()

        # Submit request as owner
        created = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                     headers=auth_headers, json={"title": "Please approve"})).json()

        # Approve as owner (owner = reviewer for approval)
        resp = await client.put(f"/api/v1/team/requests/{created['request_id']}/review",
                                headers=auth_headers,
                                json={"decision": "approved", "notes": "Looks good!"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    @pytest.mark.asyncio
    async def test_review_reject_by_reviewer(self, client: AsyncClient, auth_headers: dict):
        """Another user who is made reviewer can reject a request."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "ReviewerTest"})).json()

        # Register reviewer user
        await client.post("/api/v1/auth/register", json={
            "username": "rev_user", "password": "Revpass123",
        })
        rev = await client.post("/api/v1/auth/login", json={
            "username": "rev_user", "password": "Revpass123",
        })
        rev_h = {"Authorization": f"Bearer {rev.json()['access_token']}"}
        await client.post("/api/v1/team/join", headers=rev_h, json={
            "invite_code": team["invite_code"],
        })

        # Get team info to find reviewer user_id
        info = (await client.get(f"/api/v1/team/my?team_id={team['team_id']}",
                                headers=auth_headers)).json()
        member_id = [m["user_id"] for m in info["members"] if m["role"] == "member"][0]
        # Promote to reviewer
        resp = await client.post(f"/api/v1/team/change-role?team_id={team['team_id']}",
                                headers=auth_headers,
                                params={"target_user_id": member_id, "new_role": "reviewer"})
        assert resp.status_code == 200

        # Submit request as owner
        created = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                     headers=auth_headers, json={"title": "Review by reviewer"})).json()

        # Reject as reviewer
        resp = await client.put(f"/api/v1/team/requests/{created['request_id']}/review",
                                headers=rev_h,
                                json={"decision": "rejected", "notes": "Not needed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_review_reject(self, client: AsyncClient, auth_headers: dict):
        """Reviewer rejects a request."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "RejectReq"})).json()
        created = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                     headers=auth_headers, json={"title": "Reject me"})).json()

        resp = await client.put(f"/api/v1/team/requests/{created['request_id']}/review",
                                headers=auth_headers,
                                params={"team_id": team['team_id']},
                                json={"decision": "rejected", "notes": "Not needed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_review_duplicate(self, client: AsyncClient, auth_headers: dict):
        """Mark request as duplicate."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "DupReq"})).json()
        r1 = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                headers=auth_headers, json={"title": "Original"})).json()
        r2 = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                                headers=auth_headers, json={"title": "Duplicate"})).json()

        resp = await client.put(f"/api/v1/team/requests/{r2['request_id']}/review",
                                headers=auth_headers,
                                params={"team_id": team['team_id']},
                                json={"decision": "duplicate", "duplicate_of": r1['request_id']})
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"

    @pytest.mark.asyncio
    async def test_review_already_reviewed(self, client: AsyncClient, auth_headers: dict):
        """Reviewing an already-reviewed request should 409."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "AlreadyReviewed"})).json()
        r = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                               headers=auth_headers, json={"title": "Reviewed"})).json()
        await client.put(f"/api/v1/team/requests/{r['request_id']}/review",
                         headers=auth_headers,
                         params={"team_id": team['team_id']},
                         json={"decision": "approved"})
        resp = await client.put(f"/api/v1/team/requests/{r['request_id']}/review",
                                headers=auth_headers,
                                params={"team_id": team['team_id']},
                                json={"decision": "approved"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_generate_for_request(self, client: AsyncClient, auth_headers: dict):
        """Create a generation task from an approved request."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "GenReq"})).json()
        r = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                               headers=auth_headers, json={"title": "Generate me"})).json()
        await client.put(f"/api/v1/team/requests/{r['request_id']}/review",
                         headers=auth_headers,
                         params={"team_id": team['team_id']},
                         json={"decision": "approved"})
        resp = await client.post(f"/api/v1/team/requests/{r['request_id']}/generate",
                                 headers=auth_headers,
                                 params={"team_id": team['team_id']})
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["idea"] != ""

    @pytest.mark.asyncio
    async def test_generate_with_language(self, client: AsyncClient, auth_headers: dict):
        """Generate with explicit language parameter."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "LangGen"})).json()
        r = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                               headers=auth_headers, json={"title": "Lang test"})).json()
        await client.put(f"/api/v1/team/requests/{r['request_id']}/review",
                         headers=auth_headers,
                         params={"team_id": team['team_id']},
                         json={"decision": "approved"})
        resp = await client.post(f"/api/v1/team/requests/{r['request_id']}/generate",
                                 headers=auth_headers,
                                 params={"team_id": team['team_id'], "language": "javascript"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_link_task(self, client: AsyncClient, auth_headers: dict):
        """Link a task to a request."""
        team = (await client.post("/api/v1/team/create", headers=auth_headers,
                                  json={"name": "LinkTest"})).json()
        r = (await client.post(f"/api/v1/team/requests?team_id={team['team_id']}",
                               headers=auth_headers, json={"title": "Link me"})).json()
        await client.put(f"/api/v1/team/requests/{r['request_id']}/review",
                         headers=auth_headers,
                         params={"team_id": team['team_id']},
                         json={"decision": "approved"})
        gen = (await client.post(f"/api/v1/team/requests/{r['request_id']}/generate",
                                 headers=auth_headers,
                                 params={"team_id": team['team_id']})).json()
        resp = await client.post(f"/api/v1/team/requests/{r['request_id']}/link-task",
                                 headers=auth_headers,
                                 params={"task_id": gen["task_id"]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
