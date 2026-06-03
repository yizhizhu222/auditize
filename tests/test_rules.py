"""Test all 22 Auditize security rules.

Each rule gets at least one positive test (should trigger) and one
negative test (should not trigger a false positive).
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

from cli.rules import RULES, RULE_MAP, _walk, make_finding
from .conftest import write_file, write_binary


# ─── Helpers ─────────────────────────────────────────────────────────

def check_rule(rule_id: str, root: Path) -> list[dict]:
    """Run a single rule's check function and return findings."""
    rule = RULE_MAP.get(rule_id)
    if rule is None:
        pytest.fail(f"Rule {rule_id} not found")
    return rule["check"](root)


def assert_finds(rule_id: str, root: Path, expected: int = 1):
    """Assert rule finds exactly `expected` issues."""
    findings = check_rule(rule_id, root)
    assert len(findings) == expected, (
        f"Expected {expected} findings for {rule_id}, got {len(findings)}: "
        + str([f.get("snippet", "")[:40] for f in findings])
    )


def assert_finds_at_least(rule_id: str, root: Path, minimum: int = 1):
    """Assert rule finds at least `minimum` issues."""
    findings = check_rule(rule_id, root)
    assert len(findings) >= minimum, (
        f"Expected ≥{minimum} findings for {rule_id}, got {len(findings)}"
    )


def assert_clean(rule_id: str, root: Path):
    """Assert rule finds nothing (negative test)."""
    findings = check_rule(rule_id, root)
    assert len(findings) == 0, (
        f"Expected 0 findings for {rule_id}, got {len(findings)}: "
        + str([f.get("snippet", "")[:40] for f in findings])
    )


# ═════════════════════════════════════════════════════════════════════
# SEC-001: Hardcoded Secrets
# ═════════════════════════════════════════════════════════════════════

class TestSEC001:
    """Hardcoded API keys / secrets."""

    def test_stripe_live_key(self, tmp_project):
        p = "sk_live"
        write_file(tmp_project, "config.py", f'stripe_key = "{p}_AbCdEfGhIjKlMnOpQrStUvWxYz123456"')
        assert_finds("SEC-001", tmp_project)

    def test_aws_key(self, tmp_project):
        p = "AKIA"
        write_file(tmp_project, "aws.py", f'AWS_KEY = "{p}0123456789ABCDEF"')
        assert_finds("SEC-001", tmp_project)

    def test_github_token(self, tmp_project):
        p = "ghp"
        write_file(tmp_project, "deploy.py", f'token = "{p}_AbCdEfGhIjKlMnOpQrStUvWxYz123456AbCd"')
        assert_finds("SEC-001", tmp_project)

    def test_private_key(self, tmp_project):
        write_file(tmp_project, "key.pem", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...")
        assert_finds("SEC-001", tmp_project)

    def test_hardcoded_password(self, tmp_project):
        write_file(tmp_project, "db.py", 'password = "s3cret!Passw0rd"')
        assert_finds("SEC-001", tmp_project)

    def test_no_false_positive_env(self, tmp_project):
        """.env file should be skipped."""
        write_file(tmp_project, ".env", 'SECRET_KEY="something123"')
        assert_clean("SEC-001", tmp_project)

    def test_no_false_positive_test_password(self, tmp_project):
        """Test files with obvious placeholder passwords."""
        write_file(tmp_project, "tests/test_config.py", 'password = "your-password-here"')
        assert_clean("SEC-001", tmp_project)

    def test_no_false_positive_dummy_value(self, tmp_project):
        """Test files with dummy/placeholder password values in test dirs."""
        write_file(tmp_project, "tests/example_config.py", 'password = "test_password_placeholder"')
        assert_clean("SEC-001", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-002: .env not in gitignore
# ═════════════════════════════════════════════════════════════════════

class TestSEC002:
    def test_env_without_gitignore(self, tmp_project):
        write_file(tmp_project, ".env", "SECRET=abc123")
        # No .gitignore → should find issue
        assert_finds("SEC-002", tmp_project)

    def test_env_with_gitignore(self, tmp_project):
        write_file(tmp_project, ".env", "SECRET=abc123")
        write_file(tmp_project, ".gitignore", ".env")
        assert_clean("SEC-002", tmp_project)

    def test_no_env_file(self, tmp_project):
        assert_clean("SEC-002", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-003: Git history leak
# ═════════════════════════════════════════════════════════════════════

class TestSEC003:
    def test_no_git_repo(self, tmp_project):
        """No .git directory → no findings."""
        assert_clean("SEC-003", tmp_project)

    def test_with_git_history_leak(self, tmp_project):
        """Full git history with a leaked file requires git init."""
        try:
            subprocess.run(
                ["git", "init"], cwd=tmp_project,
                capture_output=True, timeout=5
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmp_project, capture_output=True, timeout=5
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmp_project, capture_output=True, timeout=5
            )
            # Commit a .env file
            write_file(tmp_project, ".env", "SECRET=abc")
            subprocess.run(
                ["git", "add", ".env"], cwd=tmp_project,
                capture_output=True, timeout=5
            )
            subprocess.run(
                ["git", "commit", "-m", "add env"],
                cwd=tmp_project, capture_output=True, timeout=5
            )
            # Remove from working tree but keep in history
            (tmp_project / ".env").unlink()
            assert_finds("SEC-003", tmp_project)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("git not available")


# ═════════════════════════════════════════════════════════════════════
# SEC-004: Missing .gitignore entries
# ═════════════════════════════════════════════════════════════════════

class TestSEC004:
    def test_missing_gitignore(self, tmp_project):
        assert_finds("SEC-004", tmp_project)

    def test_complete_gitignore(self, tmp_project):
        write_file(tmp_project, ".gitignore", ".env\nnode_modules\n__pycache__\n*.key")
        assert_clean("SEC-004", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-005: SSL private key files
# ═════════════════════════════════════════════════════════════════════

class TestSEC005:
    def test_key_file(self, tmp_project):
        """SEC-005 looks for 'PRIVATE KEY' in .key files."""
        write_file(tmp_project, "ssl/server.key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...")
        assert_finds("SEC-005", tmp_project)

    def test_key_file_in_deploy_dir(self, tmp_project):
        """.key files in deploy/ssl/etc directories are flagged even without PRIVATE KEY."""
        write_file(tmp_project, "deploy/server.key", "some key content")
        assert_finds("SEC-005", tmp_project)

    def test_no_key_files(self, tmp_project):
        write_file(tmp_project, "readme.txt", "hello")
        assert_clean("SEC-005", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-006: Debug statements
# ═════════════════════════════════════════════════════════════════════

class TestSEC006:
    def test_python_print(self, tmp_project):
        write_file(tmp_project, "app.py", "def hello():\n    print('debug')\n    return True")
        assert_finds("SEC-006", tmp_project)

    def test_js_console_log(self, tmp_project):
        write_file(tmp_project, "app.js", "function hello() {\n  console.log('debug');\n}")
        assert_finds("SEC-006", tmp_project)

    def test_no_debug(self, tmp_project):
        write_file(tmp_project, "app.py", "def hello():\n    return True")
        assert_clean("SEC-006", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-007: TODO/FIXME markers
# ═════════════════════════════════════════════════════════════════════

class TestSEC007:
    def test_too_many_todos(self, tmp_project):
        """SEC-007 triggers when >3 markers found (FIXME/HACK/XXX count, TODO with skip)."""
        # `# TODO` is excluded by the filter; FIXME/HACK/XXX count
        write_file(tmp_project, "app.py", (
            "# FIXME: fix this\n"
            "# HACK: ugly workaround\n"
            "# XXX: this is bad\n"
            "# BUG: known issue\n"
            "# WORKAROUND: temp fix"
        ))
        assert_finds_at_least("SEC-007", tmp_project)

    def test_few_todos(self, tmp_project):
        """Only 1-2 markers should not trigger (threshold is >3)."""
        write_file(tmp_project, "app.py", "# FIXME: one thing\n# HACK: another")
        assert_clean("SEC-007", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-008: File permissions
# ═════════════════════════════════════════════════════════════════════

class TestSEC008:
    def test_world_readable_key(self, tmp_project):
        fp = write_file(tmp_project, "secret.key", "content")
        fp.chmod(0o644)  # world-readable
        assert_finds("SEC-008", tmp_project)

    def test_restricted_permissions(self, tmp_project):
        fp = write_file(tmp_project, "secret.key", "content")
        fp.chmod(0o600)  # owner-only
        assert_clean("SEC-008", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-009: Hardcoded paths
# ═════════════════════════════════════════════════════════════════════

class TestSEC009:
    def test_home_path(self, tmp_project):
        write_file(tmp_project, "config.py", 'DATA_DIR = "/home/user/app/data"')
        assert_finds("SEC-009", tmp_project)

    def test_tmp_path(self, tmp_project):
        write_file(tmp_project, "cache.py", 'CACHE = "/tmp/cache_dir"')
        assert_finds_at_least("SEC-009", tmp_project)

    def test_no_abs_path(self, tmp_project):
        write_file(tmp_project, "config.py", 'DATA_DIR = "./data"')
        assert_clean("SEC-009", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-010: SQLite database files
# ═════════════════════════════════════════════════════════════════════

class TestSEC010:
    def test_sqlite_file(self, tmp_project):
        """SEC-010 checks for .db/.sqlite files > 1000 bytes."""
        # Must be > 1000 bytes to trigger
        write_file(tmp_project, "data.sqlite", "x" * 1001)
        assert_finds("SEC-010", tmp_project)

    def test_no_db(self, tmp_project):
        assert_clean("SEC-010", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-011: Large files
# ═════════════════════════════════════════════════════════════════════

class TestSEC011:
    def test_large_file(self, tmp_project):
        write_file(tmp_project, "big.log", "x" * (2 * 1024 * 1024))  # 2MB
        assert_finds("SEC-011", tmp_project)

    def test_small_file(self, tmp_project):
        write_file(tmp_project, "small.txt", "hello")
        assert_clean("SEC-011", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-012: Docker port exposure
# ═════════════════════════════════════════════════════════════════════

class TestSEC012:
    def test_exposed_port(self, tmp_project):
        """SEC-012 flags ANY port mapping in docker-compose.yml."""
        write_file(tmp_project, "docker-compose.yml", """
services:
  web:
    ports:
      - "3000:3000"
""")
        assert_finds("SEC-012", tmp_project)

    def test_no_docker_compose(self, tmp_project):
        write_file(tmp_project, "Dockerfile", "FROM python:3.12")
        assert_clean("SEC-012", tmp_project)

    def test_no_docker(self, tmp_project):
        assert_clean("SEC-012", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-013: Docker latest tag
# ═════════════════════════════════════════════════════════════════════

class TestSEC013:
    def test_latest_tag(self, tmp_project):
        write_file(tmp_project, "Dockerfile", "FROM python:latest")
        assert_finds("SEC-013", tmp_project)

    def test_pinned_tag(self, tmp_project):
        write_file(tmp_project, "Dockerfile", "FROM python:3.12-slim")
        assert_clean("SEC-013", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-014: Unpinned dependencies
# ═════════════════════════════════════════════════════════════════════

class TestSEC014:
    def test_unpinned_requirements(self, tmp_project):
        write_file(tmp_project, "requirements.txt", "requests>=2.0\nflask")
        assert_finds_at_least("SEC-014", tmp_project)

    def test_pinned_requirements(self, tmp_project):
        write_file(tmp_project, "requirements.txt", "requests==2.31.0\nflask==3.0.0")
        assert_clean("SEC-014", tmp_project)

    def test_unpinned_package_json(self, tmp_project):
        write_file(tmp_project, "package.json", '{"dependencies": {"express": "^4.0"}}')
        assert_finds("SEC-014", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-015: Empty catch blocks
# ═════════════════════════════════════════════════════════════════════

class TestSEC015:
    def test_python_except_pass(self, tmp_project):
        write_file(tmp_project, "app.py", "try:\n    do_something()\nexcept Exception:\n    pass")
        assert_finds("SEC-015", tmp_project)

    def test_js_empty_catch(self, tmp_project):
        """SEC-015 checks for catch blocks that are empty on a single line."""
        write_file(tmp_project, "app.js", "try {\n  doSomething();\n} catch(e) {}")
        assert_finds("SEC-015", tmp_project)

    def test_proper_error_handling(self, tmp_project):
        write_file(tmp_project, "app.py", "try:\n    do_something()\nexcept Exception as e:\n    log.error(e)")
        assert_clean("SEC-015", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-016: Missing README
# ═════════════════════════════════════════════════════════════════════

class TestSEC016:
    def test_no_readme(self, tmp_project):
        assert_finds("SEC-016", tmp_project)

    def test_has_readme(self, tmp_project):
        write_file(tmp_project, "README.md", "# My Project")
        assert_clean("SEC-016", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-017: Missing LICENSE
# ═════════════════════════════════════════════════════════════════════

class TestSEC017:
    def test_no_license(self, tmp_project):
        assert_finds("SEC-017", tmp_project)

    def test_has_license(self, tmp_project):
        write_file(tmp_project, "LICENSE", "MIT")
        assert_clean("SEC-017", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-018: Missing CI/CD
# ═════════════════════════════════════════════════════════════════════

class TestSEC018:
    def test_no_ci(self, tmp_project):
        assert_finds("SEC-018", tmp_project)

    def test_has_github_actions(self, tmp_project):
        write_file(tmp_project, ".github/workflows/test.yml", "name: CI")
        assert_clean("SEC-018", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-019: node_modules committed
# ═════════════════════════════════════════════════════════════════════

class TestSEC019:
    def test_node_modules_present(self, tmp_project):
        """SEC-019 checks if node_modules is tracked by git."""
        try:
            subprocess.run(["git", "init"], cwd=tmp_project, capture_output=True, timeout=5)
            subprocess.run(["git", "config", "user.email", "t@t.com"],
                           cwd=tmp_project, capture_output=True, timeout=5)
            subprocess.run(["git", "config", "user.name", "T"],
                           cwd=tmp_project, capture_output=True, timeout=5)
            (tmp_project / "node_modules").mkdir(parents=True)
            write_file(tmp_project, "node_modules/pkg/index.js", "module.exports = {}")
            subprocess.run(["git", "add", "node_modules"], cwd=tmp_project,
                           capture_output=True, timeout=5)
            assert_finds("SEC-019", tmp_project)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("git not available")

    def test_no_node_modules(self, tmp_project):
        assert_clean("SEC-019", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-020: Default passwords
# ═════════════════════════════════════════════════════════════════════

class TestSEC020:
    def test_admin_password(self, tmp_project):
        write_file(tmp_project, "config.py", 'ADMIN_PASSWORD = "admin123"')
        assert_finds("SEC-020", tmp_project)

    def test_safe_password(self, tmp_project):
        write_file(tmp_project, "config.py", 'ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")')
        assert_clean("SEC-020", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-021: CORS wildcard
# ═════════════════════════════════════════════════════════════════════

class TestSEC021:
    def test_cors_wildcard(self, tmp_project):
        write_file(tmp_project, "app.py", 'allow_origins = ["*"]')
        assert_finds("SEC-021", tmp_project)

    def test_specific_origin(self, tmp_project):
        write_file(tmp_project, "app.py", 'allow_origins = ["https://example.com"]')
        assert_clean("SEC-021", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# SEC-022: DEBUG mode hardcoded
# ═════════════════════════════════════════════════════════════════════

class TestSEC022:
    def test_debug_true(self, tmp_project):
        write_file(tmp_project, "settings.py", "DEBUG = True")
        assert_finds("SEC-022", tmp_project)

    def test_debug_from_env(self, tmp_project):
        write_file(tmp_project, "settings.py", 'DEBUG = os.getenv("DEBUG", "False")')
        assert_clean("SEC-022", tmp_project)


# ═════════════════════════════════════════════════════════════════════
# Test that all 22 rules are registered
# ═════════════════════════════════════════════════════════════════════

class TestRulesRegistry:
    def test_all_rules_present(self):
        assert len(RULES) == 22, f"Expected 22 rules, got {len(RULES)}"

    def test_all_rules_have_ids(self):
        for r in RULES:
            assert r["id"].startswith("SEC-"), f"Invalid rule id: {r['id']}"

    def test_rule_ids_unique(self):
        ids = [r["id"] for r in RULES]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs found"

    def test_all_rules_have_severity(self):
        valid = {"critical", "high", "medium", "low", "info"}
        for r in RULES:
            assert r["severity"] in valid, f"{r['id']} has invalid severity: {r['severity']}"

    def test_rules_have_check_functions(self):
        for r in RULES:
            assert callable(r["check"]), f"{r['id']} is missing check function"
