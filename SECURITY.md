# Security Policy

## What Auditize CLI Scans For

The CLI checks for 22 categories of issues across your project. All rules are deterministic (no AI), open source, and OWASP-referenced.

[Full rule documentation](cli/rules/README.md)

## Reporting a Vulnerability

If you find a vulnerability in the Auditize CLI itself (not in a project being scanned):

1. **Do not** open a public GitHub issue
2. Email: cjwd1234cjwd@163.com
3. Response within 48 hours

## False Positives

Auditize is designed to prefer false negatives over false positives. If you encounter a false positive:

1. Run `auditize explain <RULE_ID>` to understand the rule
2. Check if the file is being correctly identified
3. Use `auditize fix . --file <path>` to mark it as reviewed

## Responsible Use

This tool is intended for:
- Pre-deployment security review
- CI/CD pipeline integration
- Code quality auditing

It is not a replacement for:
- Professional security audit
- Penetration testing
- Compliance certification
