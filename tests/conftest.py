"""Shared test fixtures and utilities."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_project() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing."""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def write_file(root: Path, path: str, content: str) -> Path:
    """Write a file in the project root, creating parent dirs as needed."""
    fp = root / path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content)
    return fp


def write_binary(root: Path, path: str, content: bytes) -> Path:
    """Write a binary file."""
    fp = root / path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_bytes(content)
    return fp
