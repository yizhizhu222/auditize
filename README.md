# TruffleKit CLI

**Deterministic security scanner for AI-generated projects.**

Scan any codebase, get a prioritized action plan — so you review 3 files instead of 300.

```bash
pip install truffle-scan
truffle scan . --plan
```

---

## Quick Start

```bash
# Scan your project
cd your-ai-project
truffle scan .

# Get an action plan
truffle scan . --plan

# Learn about a rule
truffle explain SEC-001

# Mark issues as fixed
truffle fix .
```

## Why TruffleKit?

- **22 deterministic rules** — no AI, no hallucinations, no black box
- **OWASP-referenced** — every rule links to industry standards
- **Action plan mode** — tells you exactly what to fix, in what order
- **Fix tracking** — mark issues as fixed, track progress over time
- **Zero false positives** — prefer false negatives over false alarms
- **Open source rules** — all rules are auditable in `cli/rules/`

## Documentation

- [CLI Reference](cli/README.md)
- [Rule Library](cli/rules/README.md) — all 22 rules documented
- [Publishing Guide](cli/PUBLISH.md)

## License

MIT
