"""
Report Generator — converts scan results into plain-language reports
that non-technical users can understand.

Output is a structured report with:
  - Overall verdict (Safe / Needs Review / Dangerous) based on security + quality
  - Quality score and code quality section
  - Summary in plain English
  - Per-finding explanations in non-technical language
  - Action recommendations
"""

from __future__ import annotations

from typing import Any

from app.scanner.static_analyzer import (
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_MEDIUM,
    RISK_LOW,
    RISK_INFO,
    ScanResult,
)

RISK_EMOJI = {
    RISK_CRITICAL: "🔴",
    RISK_HIGH: "🟠",
    RISK_MEDIUM: "🟡",
    RISK_LOW: "🔵",
    RISK_INFO: "⚪",
}

RISK_LABEL = {
    RISK_CRITICAL: "Critical",
    RISK_HIGH: "High Risk",
    RISK_MEDIUM: "Medium",
    RISK_LOW: "Low",
    RISK_INFO: "Info",
}


def generate_report(result: ScanResult) -> dict[str, Any]:
    """
    Generate a human-readable safety report from a scan result.

    Now includes both security and code quality findings. Returns a
    structured dict with plain-English fields suitable for display
    to a non-technical user.
    """
    sec_score = result.total_risk_score
    qual_score = result.quality_score
    overall_score = result.overall_score
    total = len(result.findings)

    # ── Overall verdict (considers both security + quality) ──────────────────
    if total == 0:
        verdict = "safe"
        verdict_label = "✅ Safe — No Issues Found"
        verdict_description = (
            "The code passed the security check. "
            "No dangerous functions, hardcoded secrets, or suspicious patterns were detected."
        )
    elif sec_score >= 60:
        verdict = "dangerous"
        verdict_label = "🔴 Dangerous — Do Not Run"
        verdict_description = (
            "The code has serious security issues that could harm your system, "
            "leak sensitive data, or allow unauthorized access. "
            "We strongly recommend NOT running this code until the critical issues are fixed."
        )
    elif overall_score >= 50:
        verdict = "needs_review"
        verdict_label = "🟠 Needs Review — Significant Issues"
        verdict_description = (
            "The code contains a combination of security concerns and code quality issues "
            "that should be addressed before use in production."
        )
    elif qual_score >= 30:
        verdict = "needs_improvement"
        verdict_label = "🟡 Needs Improvement — Quality Issues"
        verdict_description = (
            "No critical security problems detected, but the code has notable quality issues "
            "like redundant logic, overly complex functions, or poor practices. "
            "These can lead to bugs and maintenance headaches down the road."
        )
    elif sec_score > 0:
        verdict = "minor"
        verdict_label = "🟡 Minor Security Issues"
        verdict_description = (
            "The code has a few minor security concerns, but nothing critical. "
            "Review the suggestions below for best practices."
        )
    else:
        verdict = "minor"
        verdict_label = "🔵 Minor Quality Feedback"
        verdict_description = (
            "The code is generally safe, but has some quality suggestions "
            "that can make it cleaner and more maintainable."
        )

    # ── Per-category breakdown ──────────────────────────────────────────────
    categories: dict[str, list[dict[str, Any]]] = {}
    language_map = {
        "python": "Python",
        "javascript": "JavaScript",
        "go": "Go",
        "cpp": "C++",
    }

    for finding in result.findings:
        cat = finding.category
        if cat not in categories:
            categories[cat] = []

        categories[cat].append({
            "risk_level": finding.risk_level,
            "risk_label": RISK_LABEL.get(finding.risk_level, ""),
            "risk_emoji": RISK_EMOJI.get(finding.risk_level, ""),
            "title": finding.title,
            "description": finding.description,
            "line_number": finding.line_number,
            "snippet": finding.snippet,
            "recommendation": finding.recommendation or _default_recommendation(finding.category),
            "finding_type": finding.finding_type,
        })

    # ── Separate quality-specific findings list ──────────────────────────
    quality_findings = [
        {
            "risk_level": f.risk_level,
            "risk_label": RISK_LABEL.get(f.risk_level, ""),
            "risk_emoji": RISK_EMOJI.get(f.risk_level, ""),
            "title": f.title,
            "description": f.description,
            "line_number": f.line_number,
            "snippet": f.snippet,
            "recommendation": f.recommendation or _quality_recommendation(f.category),
            "finding_type": f.finding_type,
        }
        for f in result.findings
        if f.finding_type == "quality"
    ]

    # ── Simple summary ─────────────────────────────────────────────────
    sec_count = result.total_security_findings
    qual_count = result.total_quality_findings

    if total == 0:
        simple_summary = "This code looks safe and well-written."
    elif sec_score >= 60:
        simple_summary = (
            f"This code has {total} issue{'s' if total != 1 else ''} "
            f"({sec_count} security, {qual_count} quality), "
            f"including {result.finding_count.get(RISK_CRITICAL, 0)} critical problem{'s' if result.finding_count.get(RISK_CRITICAL, 0) != 1 else ''}. "
            "You should NOT run or deploy this code until it is fixed."
        )
    elif qual_score >= 40:
        simple_summary = (
            f"This code has {qual_count} quality issue{'s' if qual_count != 1 else ''} and "
            f"{sec_count} security issue{'s' if sec_count != 1 else ''}. "
            "The quality concerns include overly complex code, redundancy, or poor practices "
            "that should be cleaned up."
        )
    elif sec_score > 0:
        simple_summary = (
            f"This code has {sec_count} security issue{'s' if sec_count != 1 else ''} to review "
            f"and {qual_count} quality suggestion{'s' if qual_count != 1 else ''}. "
            "Fix the security items first, then address the quality feedback."
        )
    elif qual_count > 0:
        simple_summary = (
            f"This code has {qual_count} quality improvement suggestion{'s' if qual_count != 1 else ''}. "
            "No security problems found — the suggestions will help make the code cleaner."
        )
    else:
        simple_summary = (
            f"This code has {total} minor issue{'s' if total != 1 else ''}. "
            "It's generally safe, but the suggestions below can make it better."
        )

    # ── What the code does (plain language) ─────────────────────────────
    what_it_does = _describe_code_behavior(result)

    # ── Build final report ──────────────────────────────────────────────
    report: dict[str, Any] = {
        "verdict": verdict,
        "verdict_label": verdict_label,
        "verdict_description": verdict_description,
        "summary": result.summary,
        "simple_summary": simple_summary,
        "what_it_does": what_it_does,
        "score": sec_score,  # Backward compat — security-only score
        "quality_score": qual_score,
        "overall_score": overall_score,
        "total_issues": total,
        "security_issues": sec_count,
        "quality_issues": qual_count,
        "finding_breakdown": result.finding_count,
        "quality_finding_breakdown": result.quality_finding_count,
        "scanned_lines": result.scanned_lines,
        "language": language_map.get(result.language, result.language),
        "categories": categories,
        "quality_findings": quality_findings,
        "findings": [f.to_dict() for f in result.findings],
    }

    return report


def _quality_recommendation(category: str) -> str:
    """Quality-specific recommendations."""
    recs = {
        "Code Quality": "Review this section. Improving code quality reduces bugs and makes maintenance easier.",
        "Complexity": "Break complex logic into smaller, focused functions for clarity.",
        "Style": "Follow consistent naming conventions and formatting for readability.",
    }
    return recs.get(category, "Clean up this area to improve code quality.")


def _default_recommendation(category: str) -> str:
    """Fallback recommendation when none is provided."""
    recs = {
        "Dangerous Function": "Replace this with a safer alternative or wrap it with strict input validation.",
        "API Key Leak": "Store this in an environment variable or secrets manager.",
        "Hardcoded Password": "Use environment variables or a secrets management service.",
        "Hardcoded Secret": "Move to environment variables or a vault service.",
        "Private Key Leak": "Remove the private key from code immediately. Use a secrets manager.",
        "Raw SQL Query": "Use parameterized queries or an ORM to prevent SQL injection.",
        "SQL Injection": "Use parameterized queries instead of string concatenation.",
        "Dangerous Pattern": "Review this pattern carefully. Consider using a safer alternative.",
        "Syntax": "Fix the syntax error before running the code.",
        "Empty Code": "Write some code first.",
        "Code Quality": "Review this code quality finding. Clean code is easier to maintain and debug.",
    }
    return recs.get(category, "Review this finding and decide if it's acceptable for your use case.")


def _describe_code_behavior(result: ScanResult) -> list[str]:
    """
    Generate a plain-language description of what the code does,
    based on the findings. This helps non-technical users understand
    the code's behavior without reading the code itself.
    """
    behaviors = []
    has_network = False
    has_filesystem = False
    has_exec = False
    has_db = False
    has_crypto = False
    has_ui = False
    has_quality_issues = False
    has_complexity = False

    for f in result.findings:
        title_lower = f.title.lower()
        if any(x in title_lower for x in ["fetch", "request", "http", "socket", "network", "xmlhttprequest"]):
            has_network = True
        if any(x in title_lower for x in ["file", "fs", "open(", "os.remove", "shutil"]):
            has_filesystem = True
        if any(x in title_lower for x in ["exec", "system(", "popen", "eval", "child_process", "shell"]):
            has_exec = True
        if any(x in title_lower for x in ["sql", "database", "db "]):
            has_db = True
        if any(x in title_lower for x in ["crypto", "cipher", "encrypt", "decrypt"]):
            has_crypto = True
        if any(x in title_lower for x in ["innerhtml", "document.write", "localstorage"]):
            has_ui = True
        if f.finding_type == "quality":
            has_quality_issues = True
        if "complex" in title_lower or "nesting" in title_lower or "complexity" in title_lower:
            has_complexity = True

    if has_ui:
        behaviors.append("• Interacts with the web page (reads/writes HTML or uses browser storage)")
    if has_network:
        behaviors.append("• Makes network requests to external servers")
    if has_filesystem:
        behaviors.append("• Reads or writes files on the server")
    if has_exec:
        behaviors.append("• Runs system commands or executes dynamically generated code")
    if has_db:
        behaviors.append("• Connects to a database")
    if has_crypto:
        behaviors.append("• Performs cryptographic operations")
    if has_quality_issues:
        behaviors.append("• Has code quality concerns that may affect reliability and maintainability")
    if has_complexity:
        behaviors.append("• Contains complex logic that could hide bugs and should be reviewed carefully")

    if not behaviors:
        behaviors.append("• Performs standard calculations and data processing")
        behaviors.append("• Does not access the network, filesystem, or system commands")

    return behaviors
