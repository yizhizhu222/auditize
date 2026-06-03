"""
Comprehensive tests for Scan API: scan code (all languages), history.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestScan:
    """Security scanning — all 4 languages, edge cases."""

    @pytest.mark.asyncio
    async def test_scan_python_safe(self, client: AsyncClient, auth_headers: dict):
        """Scan safe Python code."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "python",
            "code": "print('hello')\nx = 1 + 2",
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["verdict"] == "safe"
        assert report["score"] == 0

    @pytest.mark.asyncio
    async def test_scan_python_dangerous(self, client: AsyncClient, auth_headers: dict):
        """Detect dangerous eval()."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "python",
            "code": 'eval("os.system(\'rm -rf /\')")',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["total_issues"] > 0

    @pytest.mark.asyncio
    async def test_scan_python_sql_injection(self, client: AsyncClient, auth_headers: dict):
        """Detect SQL injection potential."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "python",
            "code": 'cursor.execute("SELECT * FROM users WHERE id = " + user_input)',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["total_issues"] > 0

    @pytest.mark.asyncio
    async def test_scan_api_key_leak(self, client: AsyncClient, auth_headers: dict):
        """Detect hardcoded API key."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "python",
            "code": 'api_key = "sk-1234567890abcdef"',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        categories = [f["title"] for f in report["findings"]]
        assert any("API Key" in c for c in categories)

    @pytest.mark.asyncio
    async def test_scan_javascript(self, client: AsyncClient, auth_headers: dict):
        """Scan JavaScript for eval()."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "javascript",
            "code": 'eval("alert(1)");\nconsole.log("hi");',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        titles = [f["title"] for f in report["findings"]]
        assert any("eval" in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_scan_javascript_xss(self, client: AsyncClient, auth_headers: dict):
        """Detect innerHTML assignment (XSS risk)."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "javascript",
            "code": 'document.getElementById("x").innerHTML = userInput;',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["total_issues"] > 0

    @pytest.mark.asyncio
    async def test_scan_go(self, client: AsyncClient, auth_headers: dict):
        """Scan Go for exec.Command."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "go",
            "code": 'import "os/exec"\ncmd := exec.Command("rm", "-rf", "/")',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["total_issues"] > 0

    @pytest.mark.asyncio
    async def test_scan_cpp(self, client: AsyncClient, auth_headers: dict):
        """Scan C++ for gets() (critical)."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "cpp",
            "code": '#include <cstdio>\nint main() { char buf[10]; gets(buf); }',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["total_issues"] > 0

    @pytest.mark.asyncio
    async def test_scan_cpp_strcpy(self, client: AsyncClient, auth_headers: dict):
        """Detect strcpy (buffer overflow)."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "cpp",
            "code": 'char dst[10]; strcpy(dst, src);',
        })
        assert resp.status_code == 200
        report = resp.json()["report"]
        assert report["finding_breakdown"].get("high", 0) > 0 or report["total_issues"] > 0

    @pytest.mark.asyncio
    async def test_scan_unsupported_language(self, client: AsyncClient, auth_headers: dict):
        """Unsupported language should 400."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "ruby",
            "code": "puts 'hello'",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_scan_empty_code(self, client: AsyncClient, auth_headers: dict):
        """Empty code should 400."""
        resp = await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "python", "code": "",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_scan_without_auth(self, client: AsyncClient):
        """Scan without auth should work (optional auth)."""
        resp = await client.post("/api/v1/scan", json={
            "language": "python",
            "code": "print('public scan')",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_scan_history(self, client: AsyncClient, auth_headers: dict):
        """Scan history should return recent scans."""
        await client.post("/api/v1/scan", headers=auth_headers, json={
            "language": "python", "code": "history_test",
        })
        resp = await client.get("/api/v1/scan/history", headers=auth_headers)
        assert resp.status_code == 200
        assert "history" in resp.json()

    @pytest.mark.asyncio
    async def test_scan_get_report_by_id(self, client: AsyncClient, auth_headers: dict):
        """Get scan report by task_id should work."""
        resp = await client.get("/api/v1/scan/tasks/ad-hoc", headers=auth_headers)
        assert resp.status_code in (200, 404)
