#!/usr/bin/env bash
# ── Auditize pre-commit hook (standalone, no pre-commit framework) ──
# Install:
#   cp scripts/pre-commit.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
# ─────────────────────────────────────────────────────────────────────
echo "🔍  Auditize: scanning staged files..."

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|ts|jsx|tsx|go|rs|java)$' || true)

if [ -z "$STAGED_FILES" ]; then
    echo "✅  No staged files to scan."
    exit 0
fi

if ! command -v auditize &> /dev/null; then
    echo "❌  auditize not installed. Run: pip install auditize"
    exit 1
fi

auditize scan . --quick --json > /tmp/auditize-precommit.json 2>/dev/null

CRITICAL=$(python3 -c "
import json
with open('/tmp/auditize-precommit.json') as f:
    data = json.load(f)
print(data.get('severity_counts', {}).get('critical', 0))
" 2>/dev/null || echo "0")

if [ "$CRITICAL" -gt "0" ]; then
    echo "❌  Critical security issues found! Run: auditize scan ."
    auditize scan . --quick
    exit 1
fi

echo "✅  Auditize: no critical issues."
exit 0
