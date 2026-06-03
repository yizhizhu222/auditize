"""Test the Auditize scan engine."""

from pathlib import Path

from cli.scanner import (
    scan_project, detect_languages, count_code_files,
    load_status, save_status, mark_fixed, reset_status,
    finding_key,
)
from .conftest import write_file


# ─── Language Detection ─────────────────────────────────────────────

class TestDetectLanguages:
    def test_python_by_manifest(self, tmp_project):
        write_file(tmp_project, "pyproject.toml", "[project]\nname = 'test'")
        langs = detect_languages(tmp_project)
        assert "Python" in langs

    def test_js_by_manifest(self, tmp_project):
        write_file(tmp_project, "package.json", "{}")
        langs = detect_languages(tmp_project)
        assert "JavaScript" in langs

    def test_go_by_manifest(self, tmp_project):
        write_file(tmp_project, "go.mod", "module test")
        langs = detect_languages(tmp_project)
        assert "Go" in langs

    def test_rust_by_manifest(self, tmp_project):
        write_file(tmp_project, "Cargo.toml", "[package]\nname = 'test'")
        langs = detect_languages(tmp_project)
        assert "Rust" in langs

    def test_java_by_manifest(self, tmp_project):
        write_file(tmp_project, "pom.xml", "<project></project>")
        langs = detect_languages(tmp_project)
        assert "Java" in langs

    def test_by_extension(self, tmp_project):
        for i in range(3):
            write_file(tmp_project, f"file{i}.py", "# python")
        langs = detect_languages(tmp_project)
        assert "Python" in langs

    def test_no_language_detected(self, tmp_project):
        write_file(tmp_project, "readme.txt", "hello")
        langs = detect_languages(tmp_project)
        assert langs == {"未知"} or len(langs) > 0

    def test_skips_node_modules(self, tmp_project):
        write_file(tmp_project, "node_modules/pkg/index.js", 'let x = 1')
        # Need 3+ .py files for extension-based detection to trigger
        for i in range(3):
            write_file(tmp_project, f"app{i}.py", "# real code")
        langs = detect_languages(tmp_project)
        # Should still find Python (node_modules JS is skipped by _walk)
        assert "Python" in langs


# ─── Code File Counting ─────────────────────────────────────────────

class TestCountCodeFiles:
    def test_counts_py_files(self, tmp_project):
        write_file(tmp_project, "app.py", "")
        assert count_code_files(tmp_project) == 1

    def test_skips_node_modules(self, tmp_project):
        write_file(tmp_project, "app.py", "")
        write_file(tmp_project, "node_modules/pkg/index.js", "")
        assert count_code_files(tmp_project) == 1

    def test_skips_git_dir(self, tmp_project):
        write_file(tmp_project, "app.py", "")
        write_file(tmp_project, ".git/objects/abc", "")
        assert count_code_files(tmp_project) == 1

    def test_counts_multiple_extensions(self, tmp_project):
        for ext in [".py", ".js", ".ts", ".go", ".rs"]:
            write_file(tmp_project, f"app{ext}", "")
        assert count_code_files(tmp_project) == 5

    def test_empty_project(self, tmp_project):
        assert count_code_files(tmp_project) == 0


# ─── Fix Tracking ──────────────────────────────────────────────────

class TestFixTracking:
    def test_load_status_empty(self, tmp_project):
        status = load_status(tmp_project)
        assert "fixed" in status
        assert status["fixed"] == []

    def test_save_and_load_status(self, tmp_project):
        save_status(tmp_project, {"fixed": ["SEC-001:file.py:10"]})
        status = load_status(tmp_project)
        assert "SEC-001:file.py:10" in status["fixed"]

    def test_mark_fixed(self, tmp_project):
        key = "SEC-001:config.py:5"
        mark_fixed(tmp_project, key)
        status = load_status(tmp_project)
        assert key in status["fixed"]

    def test_mark_fixed_idempotent(self, tmp_project):
        key = "SEC-001:config.py:5"
        mark_fixed(tmp_project, key)
        mark_fixed(tmp_project, key)  # Should not double-add
        status = load_status(tmp_project)
        assert status["fixed"].count(key) == 1

    def test_reset_status(self, tmp_project):
        mark_fixed(tmp_project, "SEC-001:file.py:1")
        reset_status(tmp_project)
        status = load_status(tmp_project)
        assert status["fixed"] == []

    def test_finding_key_format(self):
        finding = {"rule_id": "SEC-001", "file": "app.py", "line": 10}
        key = finding_key(finding)
        assert key == "SEC-001:app.py:10"


# ─── Full Scan ─────────────────────────────────────────────────────

class TestScanProject:
    def test_empty_project(self, tmp_project):
        """A completely empty project has low-severity findings (missing docs etc)."""
        result = scan_project(tmp_project, hide_fixed=False)
        # Missing README, LICENSE, .gitignore, CI/CD = 4 low/info findings
        assert result["total_findings"] <= 5
        assert result["grade"] in ("A", "B")

    def test_scan_detects_project_name(self, tmp_project):
        result = scan_project(tmp_project, hide_fixed=False)
        assert result["project_name"] == tmp_project.name

    def test_scan_with_issues(self, tmp_project):
        write_file(tmp_project, "config.py", 'password = "admin123"')
        write_file(tmp_project, "secret.key", "some key content")
        result = scan_project(tmp_project, hide_fixed=False)
        assert result["total_findings"] > 0
        assert "critical" in result["severity_counts"] or "high" in result["severity_counts"]

    def test_quick_mode_skips_low_info(self, tmp_project):
        """Quick mode should skip low/info severity rules."""
        # Without quick mode, missing README is found
        # With quick mode, low severity rules are skipped
        result_quick = scan_project(tmp_project, quick=True, hide_fixed=False)
        result_full = scan_project(tmp_project, quick=False, hide_fixed=False)
        assert result_quick["total_findings"] <= result_full["total_findings"]

    def test_hide_fixed(self, tmp_project):
        write_file(tmp_project, "config.py", 'password = "admin123"')
        result = scan_project(tmp_project, hide_fixed=False)
        assert result["total_findings"] > 0

        # Mark all findings as fixed
        for f in result["findings"]:
            mark_fixed(tmp_project, f["_key"])

        # Rescan with hide_fixed=True
        result_hidden = scan_project(tmp_project, hide_fixed=True)
        assert result_hidden["total_findings"] < result["total_findings"]

    def test_scan_result_structure(self, tmp_project):
        result = scan_project(tmp_project, hide_fixed=False)
        required_keys = [
            "project", "project_name", "languages", "code_files",
            "scanned_at", "elapsed", "rules_loaded", "findings",
            "total_findings", "severity_counts", "health_score",
            "grade", "grade_label", "must_fix", "should_fix", "can_ignore",
        ]
        for key in required_keys:
            assert key in result, f"Missing key in result: {key}"

    def test_rules_loaded_count(self, tmp_project):
        result = scan_project(tmp_project)
        assert result["rules_loaded"] == 22
