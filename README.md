<p align="center">
  <img src="https://img.shields.io/badge/Auditize-v0.1.1-blue?style=flat-square" alt="Auditize">
</p>

<p align="center">
  <b>Deterministic security scanner for AI-generated and human-written code.</b><br>
  Scan any project. Get a prioritized action plan. Review 3 files instead of 300.
</p>

<p align="center">
  <a href="https://pypi.org/project/auditize-cli/">
    <img src="https://img.shields.io/pypi/v/auditize-cli?style=flat-square" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/auditize-cli/">
    <img src="https://img.shields.io/pypi/pyversions/auditize-cli?style=flat-square" alt="Python">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/yizhizhu222/auditize?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/yizhizhu222/auditize/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/yizhizhu222/auditize/scan.yml?branch=main&style=flat-square" alt="CI">
  </a>
  <a href="https://pre-commit.com">
    <img src="https://img.shields.io/badge/pre--commit-ready-brightgreen?style=flat-square" alt="pre-commit">
  </a>
  <a href="https://github.com/yizhizhu222/auditize">
    <img src="https://img.shields.io/github/stars/yizhizhu222/auditize?style=flat-square" alt="Stars">
  </a>
</p>

---

## What is Auditize?

Auditize scans your project for **22 categories** of security and quality issues — hardcoded secrets, debug artifacts, misconfigured Docker, missing CI/CD, and more.

Each rule is:
- **Deterministic** — pure pattern matching. Zero AI hallucinations.
- **Verifiable** — every finding cites a file, a line number, and the matched code.
- **OWASP-referenced** — backed by real security research.

Review your entire project in seconds. Not hours.

---

## Quick Start

```bash
# Install
pip install auditize-cli

# Scan the current project
auditize scan .

# Get a todo-style action plan
auditize scan . --plan

# Integrate into CI
auditize scan . --json
```

**Zero dependencies. Zero config.**

---

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **22 rules, 3 critical** | Secrets, SSL keys, debug code, Docker, CORS, git leaks |
| 🎯 **Action plan mode** | `--plan` gives a checklist: "fix these 3 first, then these 2" |
| 📊 **Health score + grade** | A–D grading with visual score bar |
| ✅ **Fix tracking** | Mark issues as fixed; they disappear from future scans |
| 🔗 **CI-ready JSON** | `--json` for pipeline integration |
| 🛡️ **Zero false positives** | Prefers false negatives over noise |
| 📖 **Open source rules** | Each rule has a detailed explainer (`auditize explain SEC-001`) |
| 📦 **Zero dependencies** | Uses only the Python standard library |

---

## Output Modes

### Default: Health bar + key items

```
  Auditize v0.1.1  —  Deterministic Security Review  ·  22 rules

  Project: my-app  (Python, JavaScript)
  Files: 47 code files  |  Rules: 22

  Health   ████████████████░░░  B  (72/100)

  Critical: 1  |  High: 2  |  Medium: 3

  ─── Must Fix ──────────────────────────────────────────
  🔴 SEC-001  API Key hardcoded
       config.py:15  →  API_KEY = 'sk_live_...'
       Fix: Move to .env

  🟠 SEC-005  SSL key file in project
       deploy/server.key:1  →  Private key found
       Fix: Remove from repo

  ─── Should Fix ────────────────────────────────────────
  🟡 SEC-014  Unpinned dependency
       requirements.txt:3  →  django>=4.0
       Fix: Pin to django==4.2.16
```

### Plan mode: Checklist

```
  📋 Action Plan — my-app

  Step 1: Must Fix (3 items · 13 min)
  □  1. SEC-001  Hardcoded API key
         config.py:15  →  API_KEY = 'sk_live_...'
       ✓ Fixed? Next scan will auto-detect.

  Step 2: Should Fix (2 items · 5 min)
  □  4. SEC-014  Unpinned dependency
         requirements.txt:3  →  django>=4.0
```

### JSON mode: CI integration

```bash
auditize scan . --json > report.json
```

---

## Rules (22 total)

| ID | Category | Severity | Checks |
|----|----------|----------|--------|
| SEC-001 | Secret Leak | 🔴 critical | Hardcoded API keys, passwords, tokens |
| SEC-002 | Secret Leak | 🟠 high | `.env` not in `.gitignore` |
| SEC-003 | Git Leak | 🟠 high | Git history contains sensitive files |
| SEC-004 | Git Leak | 🟡 medium | `.gitignore` missing essential entries |
| SEC-005 | SSL | 🔴 critical | SSL private key files in project |
| SEC-006 | Debug | 🟡 medium | Debug statements in production code |
| SEC-007 | Code Marker | 🔵 low | Accumulated TODO/FIXME markers |
| SEC-008 | File Permission | 🟡 medium | World-readable sensitive files |
| SEC-009 | Path | 🟡 medium | Hardcoded absolute paths |
| SEC-010 | Database | 🟠 high | SQLite DB files web-accessible |
| SEC-011 | Large File | 🔵 low | Files >1MB in repo |
| SEC-012 | Docker | 🟡 medium | Publicly exposed ports |
| SEC-013 | Docker | 🔵 low | `:latest` tag used |
| SEC-014 | Dependency | 🟡 medium | Unpinned version ranges |
| SEC-015 | Error Handling | 🟡 medium | Empty catch/except blocks |
| SEC-016 | Documentation | 🔵 low | Missing README |
| SEC-017 | Documentation | 🔵 low | Missing LICENSE |
| SEC-018 | CI/CD | ⚪ info | Missing CI/CD configuration |
| SEC-019 | Dependency | 🔵 low | `node_modules` tracked by git |
| SEC-020 | Security Config | 🔴 critical | Default admin passwords |
| SEC-021 | Security Config | 🟡 medium | CORS wildcard (`*`) |
| SEC-022 | Security Config | 🟠 high | DEBUG mode hardcoded True |

---

## Why not use X?

| | Auditize | Gitleaks | Semgrep | Snyk | linter |
|---|---|---|---|---|---|
| **Zero deps** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Fix tracking** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Action plan** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Secrets scan** | ✅ | ✅ | partial | ✅ | ❌ |
| **Docker scan** | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Git history** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Open source rules** | ✅ | ❌ | ✅ | ❌ | ✅ |
| **No AI (deterministic)** | ✅ | ✅ | ✅ | ❌ | ✅ |

Auditize isn't trying to replace dedicated tools — it's a **catch-all first pass** that runs in seconds with zero setup.

---

## Installation

```bash
# Via pip
pip install auditize-cli

# Via pipx (isolated)
pipx install auditize

# Via pre-commit
# Add to .pre-commit-config.yaml:
#   - repo: https://github.com/yizhizhu222/auditize
#     rev: v0.1.1
#     hooks:
#       - id: auditize-scan
```

## CI/CD Integration

```yaml
name: Security Scan
on: [push, pull_request]
jobs:
  auditize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install auditize-cli
      - run: auditize scan . --json > report.json
      - run: |
          python3 -c "
          import json
          d = json.load(open('report.json'))
          assert d['severity_counts'].get('critical', 0) == 0, 'Critical issues found!'
          "
```

---

## Documentation

- [CLI Reference](cli/README.md) — full command reference (Chinese)
- [Rule Library](cli/rules/README.md) — all 22 rules documented
- [Publishing Guide](cli/PUBLISH.md) — PyPI release process

## Development

```bash
git clone https://github.com/yizhizhu222/auditize.git
cd auditize
pip install -e ".[test]"
pytest tests/ -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT
