# Contributing to Auditize

Thanks for your interest! Auditize is open source and contributions are welcome.

## Quick Start

```bash
git clone https://github.com/yizhizhu222/auditize.git
cd auditize
pip install -e ".[test]"
pytest tests/ -v
```

## Development Guidelines

### Adding a new rule

Rules live in `cli/rules.py` as decorated functions. Each rule needs:

1. **`@register` decorator** with: `id`, `category`, `severity`, `title`, `description`, `recommendation`, `reference`
2. **A check function** that receives `root: Path` and returns a list of findings
3. **A markdown doc** in `cli/rules/SEC-NNN.md`

See SEC-001 for a good example.

### Code style

- Python 3.8+ compatible
- No external dependencies (stdlib only)
- Keep functions focused and testable
- Prefer false negatives over false positives

### Testing

- All rules must have positive and negative tests in `tests/test_rules.py`
- Run tests before submitting: `pytest tests/ -v`
- Tests should be fast (< 1s total)

### Commit messages

Format: `type(scope): description`

Examples:
```
feat(rules): add SEC-023 for insecure randomness
fix(scanner): handle edge case in git history check
docs(readme): add CI integration example
test(scanner): add quick mode test
```

## Pull Request Process

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-rule`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Push and open a PR
6. Link any related issues

## Reporting Issues

- **Security vulnerabilities**: Email cjwd1234cjwd@163.com (not public issues)
- **False positives**: Include the file content and `auditize explain <RULE_ID>` output
- **Feature requests**: Describe the use case, not just the solution

## License

By contributing, you agree that your contributions will be licensed under MIT.
