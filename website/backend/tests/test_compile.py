"""
Tests for the code playground compile/run API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compile_cpp_hello(client: AsyncClient, auth_headers: dict):
    """Compile and run a simple C++ program."""
    resp = await client.post("/api/v1/compile", json={
        "language": "cpp",
        "code": '#include <iostream>\nint main() { std::cout << "Hello"; return 0; }',
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "Hello" in data["stdout"]
    assert data["exit_code"] == 0


@pytest.mark.asyncio
async def test_compile_cpp_error(client: AsyncClient, auth_headers: dict):
    """C++ code with compilation error."""
    resp = await client.post("/api/v1/compile", json={
        "language": "cpp",
        "code": "int main() { this_is_not_valid }",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "compile_error"


@pytest.mark.asyncio
async def test_compile_python(client: AsyncClient, auth_headers: dict):
    """Run a Python script."""
    resp = await client.post("/api/v1/compile", json={
        "language": "python3",
        "code": "print(42)",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "42" in data["stdout"]


@pytest.mark.asyncio
async def test_compile_javascript(client: AsyncClient, auth_headers: dict):
    """Run JavaScript."""
    resp = await client.post("/api/v1/compile", json={
        "language": "javascript",
        "code": "console.log('JS OK')",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "JS OK" in data["stdout"]


go = pytest.mark.skipif(not __import__('shutil').which('go'), reason="Go not installed on this system")

@pytest.mark.asyncio
@go
async def test_compile_go(client: AsyncClient, auth_headers: dict):
    """Run Go (requires Go installed)."""
    resp = await client.post("/api/v1/compile", json={
        "language": "go",
        "code": 'package main\nimport "fmt"\nfunc main() { fmt.Println("Go OK") }',
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "Go OK" in data["stdout"]


@pytest.mark.asyncio
async def test_compile_empty_code(client: AsyncClient, auth_headers: dict):
    """Empty code should 400."""
    resp = await client.post("/api/v1/compile", json={
        "language": "cpp", "code": "",
    }, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_compile_unknown_language(client: AsyncClient, auth_headers: dict):
    """Unknown language should 400."""
    resp = await client.post("/api/v1/compile", json={
        "language": "brainfuck", "code": "+++",
    }, headers=auth_headers)
    assert resp.status_code == 400
