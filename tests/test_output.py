"""Test Auditize output modes."""

import json
from cli.output import print_default, print_verbose, print_plan, print_json, print_explain, print_rules_list


def make_result(**overrides) -> dict:
    """Create a minimal scan result for testing output."""
    result = {
        "project": "/tmp/test",
        "project_name": "test",
        "languages": ["Python"],
        "code_files": 10,
        "scanned_at": "2024-01-01T00:00:00",
        "elapsed": 0.42,
        "rules_loaded": 22,
        "findings": [
            {
                "rule_id": "SEC-001",
                "rule_title": "Hardcoded Secret",
                "severity": "critical",
                "file": "config.py",
                "line": 5,
                "snippet": "API_KEY = 'sk_live_...'",
                "recommendation": "Use env var",
                "reference": "https://example.com",
                "category": "Secret Leak",
                "_key": "SEC-001:config.py:5",
                "_fixed": False,
            },
            {
                "rule_id": "SEC-006",
                "rule_title": "Debug Statement",
                "severity": "medium",
                "file": "app.py",
                "line": 10,
                "snippet": "print('debug')",
                "recommendation": "Remove print",
                "reference": "",
                "category": "Debug Artifact",
                "_key": "SEC-006:app.py:10",
                "_fixed": False,
            },
        ],
        "total_findings": 2,
        "severity_counts": {"critical": 1, "medium": 1},
        "score": 30,
        "health_score": 70,
        "grade": "B",
        "grade_label": "良好 — 建议上线前审查",
        "must_fix": [
            {
                "rule_id": "SEC-001",
                "rule_title": "Hardcoded Secret",
                "severity": "critical",
                "file": "config.py",
                "line": 5,
                "snippet": "API_KEY = 'sk_live_...'",
                "recommendation": "Use env var",
            },
        ],
        "should_fix": [
            {
                "rule_id": "SEC-006",
                "rule_title": "Debug Statement",
                "severity": "medium",
                "file": "app.py",
                "line": 10,
                "snippet": "print('debug')",
                "recommendation": "Remove print",
            },
        ],
        "can_ignore": [],
    }
    result.update(overrides)
    return result


class TestOutput:
    """Output functions should not crash with valid input."""

    def test_json_output_valid_json(self, capsys):
        result = make_result()
        print_json(result)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["project"] == "/tmp/test"
        assert len(parsed["findings"]) == 2
        assert parsed["findings"][0]["rule_id"] == "SEC-001"

    def test_json_output_fields(self, capsys):
        result = make_result()
        print_json(result)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        for key in ["project", "health_score", "grade", "total_findings", "severity_counts"]:
            assert key in parsed

    def test_default_output_runs(self, capsys):
        result = make_result()
        print_default(result)
        captured = capsys.readouterr()
        assert "Auditize" in captured.out
        assert "SEC-001" in captured.out

    def test_verbose_output_runs(self, capsys):
        result = make_result()
        print_verbose(result)
        captured = capsys.readouterr()
        assert "SEC-001" in captured.out

    def test_plan_output_runs(self, capsys):
        result = make_result()
        print_plan(result)
        captured = capsys.readouterr()
        assert "SEC-001" in captured.out

    def test_empty_findings_default(self, capsys):
        result = make_result(findings=[], total_findings=0,
                            severity_counts={}, score=0, health_score=100,
                            grade="A", grade_label="安全 — 未发现问题",
                            must_fix=[], should_fix=[], can_ignore=[])
        print_default(result)
        captured = capsys.readouterr()
        assert "Auditize" in captured.out

    def test_explain_known_rule(self, capsys):
        print_explain("SEC-001")
        captured = capsys.readouterr()
        assert "SEC-001" in captured.out

    def test_explain_unknown_rule(self, capsys):
        print_explain("SEC-999")
        captured = capsys.readouterr()
        assert "未找到" in captured.out or "not found" in captured.out.lower() or "SEC-999" in captured.out

    def test_rules_list_output(self, capsys):
        print_rules_list()
        captured = capsys.readouterr()
        assert "SEC-001" in captured.out
