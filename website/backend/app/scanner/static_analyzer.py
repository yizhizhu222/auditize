"""
Static Code Analyzer — scans source code for security risks, dangerous patterns,
code quality issues, logical errors, and suspicious behavior.

Analysis categories:
  - Dangerous functions (eval, exec, system, etc.)
  - Injection risks (SQL injection, command injection)
  - Sensitive information leaks (hardcoded keys, passwords)
  - File system access (read/write unexpected paths)
  - Network access (outbound connections)
  - Cryptography misuse
  - Code quality: complexity, redundancy, naming, dead code
  - Best practices: error handling, magic numbers, documentation
"""

from __future__ import annotations

import ast
import logging
import re
from collections import Counter
from typing import Any

log = logging.getLogger(__name__)

# ── Risk levels ───────────────────────────────────────────────────────────────
RISK_CRITICAL = "critical"
RISK_HIGH = "high"
RISK_MEDIUM = "medium"
RISK_LOW = "low"
RISK_INFO = "info"

RISK_WEIGHTS = {
    RISK_CRITICAL: 40,
    RISK_HIGH: 20,
    RISK_MEDIUM: 10,
    RISK_LOW: 5,
    RISK_INFO: 0,
}

# ── Rule definitions ──────────────────────────────────────────────────────────

DANGEROUS_FUNCTIONS = {
    # Python
    "eval": "Evaluates arbitrary Python expressions. Can execute system commands.",
    "exec": "Executes arbitrary Python code. Full system access risk.",
    "__import__": "Dynamic import — can load unexpected modules.",
    "compile": "Compiles arbitrary code at runtime. Code injection risk.",
    # Shell / OS
    "os.system": "Executes shell commands. Full command injection risk.",
    "os.popen": "Opens a pipe to a shell command. Command injection risk.",
    "subprocess.call": "Runs a system command. Risk of command injection.",
    "subprocess.run": "Runs a system command. Risk of command injection.",
    "subprocess.Popen": "Runs a system command. Risk of command injection.",
    "shutil.rmtree": "Deletes entire directory trees. Destructive operation.",
    # File operations
    "open": "Opens a file. Check that the path is not user-controlled.",
    "os.remove": "Deletes a file — potentially destructive.",
    "os.unlink": "Deletes a file — potentially destructive.",
    "os.chmod": "Changes file permissions — risk of privilege escalation.",
    # Network
    "requests.get": "Makes HTTP GET request. Unexpected outbound connection.",
    "requests.post": "Makes HTTP POST request. Data exfiltration risk.",
    "urllib.request.urlopen": "Opens arbitrary URLs. SSRF risk.",
    "socket.connect": "Opens a raw network connection. Data exfiltration risk.",
    # Serialization
    "pickle.load": "Can execute arbitrary code during deserialization.",
    "pickle.loads": "Can execute arbitrary code during deserialization.",
    "shelve.open": "Uses pickle internally — code execution risk.",
}

SENSITIVE_PATTERNS: list[tuple[str, str, str, str]] = [
    # (pattern, risk_level, category, explanation)
    (r"(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['\"][^'\"]+['\"]", RISK_HIGH,
     "API Key Leak", "Found what looks like a hardcoded API key. Keys should use environment variables."),
    (r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]+['\"]", RISK_HIGH,
     "Hardcoded Password", "A password appears to be hardcoded. Use environment variables or a secrets manager."),
    (r"(?i)(?:secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", RISK_MEDIUM,
     "Hardcoded Secret", "A secret or token appears hardcoded in the source."),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", RISK_CRITICAL,
     "Private Key Leak", "A private key is embedded in the source code. This is a critical security risk."),
    (r"(?:INSERT|UPDATE|DELETE)\s+(?:INTO\s+)?\w+\s", RISK_MEDIUM,
     "Raw SQL Query", "Found a raw SQL statement. Risk of SQL injection if user input is interpolated."),
    (r"\.format\(.*\)", RISK_LOW,
     "String Formatting in SQL", "String formatting in SQL context can lead to injection."),
    (r"f['\"].*\{.*\}.*['\"]", RISK_INFO,
     "F-string (review)", "F-strings are generally safe, but ensure no user data is interpolated into SQL."),
]

SQL_INJECTION_PATTERNS = [
    r"(?i)SELECT\s+.*\s+FROM\s+.*\s*\+\s*",
    r"(?i)WHERE\s+.*\s*=\s*['\"].*\+\s*",
    r"(?i)cursor\.execute\(['\"].*\+",
    r"(?i)cursor\.execute\(f['\"]",
]


class ScanFinding:
    """A single security or quality finding."""

    def __init__(
        self,
        category: str,
        risk_level: str,
        title: str,
        description: str,
        line_number: int | None = None,
        snippet: str | None = None,
        recommendation: str | None = None,
        finding_type: str = "security",  # "security" or "quality"
    ):
        self.category = category
        self.risk_level = risk_level
        self.title = title
        self.description = description
        self.line_number = line_number
        self.snippet = snippet
        self.recommendation = recommendation
        self.finding_type = finding_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "risk_level": self.risk_level,
            "title": self.title,
            "description": self.description,
            "line_number": self.line_number,
            "snippet": self.snippet,
            "recommendation": self.recommendation,
            "finding_type": self.finding_type,
        }


class ScanResult:
    """Result of a full scan — security + code quality."""

    def __init__(self, language: str, code_snippet: str):
        self.language = language
        self.code_snippet = code_snippet
        self.findings: list[ScanFinding] = []
        self._scanned_lines = len(code_snippet.splitlines())

    def add(self, finding: ScanFinding) -> None:
        self.findings.append(finding)

    @property
    def total_risk_score(self) -> int:
        """0-100 where 100 is most dangerous (security only)."""
        score = 0
        for f in self.findings:
            if f.finding_type == "security":
                score += RISK_WEIGHTS.get(f.risk_level, 0)
        return min(score, 100)

    @property
    def quality_score(self) -> int:
        """0-100 where 100 is worst quality (quality issues only)."""
        score = 0
        for f in self.findings:
            if f.finding_type == "quality":
                score += RISK_WEIGHTS.get(f.risk_level, 0)
        return min(score, 100)

    @property
    def overall_score(self) -> int:
        """Combined security + quality score, 0-100."""
        return min(self.total_risk_score + self.quality_score, 100)

    @property
    def finding_count(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.risk_level] = counts.get(f.risk_level, 0) + 1
        return counts

    @property
    def quality_finding_count(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            if f.finding_type == "quality":
                counts[f.risk_level] = counts.get(f.risk_level, 0) + 1
        return counts

    @property
    def total_security_findings(self) -> int:
        return sum(1 for f in self.findings if f.finding_type == "security")

    @property
    def total_quality_findings(self) -> int:
        return sum(1 for f in self.findings if f.finding_type == "quality")

    @property
    def summary(self) -> str:
        """One-line summary in plain language."""
        sec = self.total_security_findings
        qual = self.total_quality_findings
        total = len(self.findings)
        if total == 0:
            return "No issues found. The code looks clean."
        parts = []
        if sec:
            parts.append(f"{sec} security issue{'s' if sec > 1 else ''}")
        if qual:
            parts.append(f"{qual} quality issue{'s' if qual > 1 else ''}")
        return f"Found {total} issue{'s' if total != 1 else ''}: {', '.join(parts)}."

    @property
    def scanned_lines(self) -> int:
        return self._scanned_lines

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "scanned_lines": self._scanned_lines,
            "total_risk_score": self.total_risk_score,
            "quality_score": self.quality_score,
            "overall_score": self.overall_score,
            "finding_counts": self.finding_count,
            "quality_finding_counts": self.quality_finding_count,
            "total_security_findings": self.total_security_findings,
            "total_quality_findings": self.total_quality_findings,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Code Quality Analyzer — detects logical errors, redundant code, bad practices
# ═══════════════════════════════════════════════════════════════════════════════

class CodeQualityAnalyzer:
    """
    Analyzes Python code for quality issues:
      - Cyclomatic complexity (too many branches)
      - Overly long functions
      - Empty exception handlers (except: pass)
      - Too many parameters
      - Unused variables
      - Deep nesting
      - Magic numbers
      - Overly long lines
      - Dead code (unreachable after return/raise)
      - TODO/FIXME comments
      - Missing docstrings
      - Unnecessary `else` after return/raise/break
      - Duplicate code blocks
      - Too many return points
      - Overly broad exception handlers (bare `except:`)
      - Variable shadowing
      - Redundant pass statements
      - Missing __init__ in classes
    """

    # pylint: disable=too-many-public-methods

    def analyze(self, code: str, result: ScanResult) -> None:
        """Run all quality checks and add findings to result."""
        lines = code.splitlines()
        if not lines:
            return

        try:
            tree = ast.parse(code)
            self._check_complexity(tree, code, result)
            self._check_long_functions(tree, code, result)
            self._check_empty_handlers(tree, result)
            self._check_too_many_params(tree, result)
            self._check_unused_vars(tree, result)
            self._check_nesting_depth(tree, code, result)
            self._check_magic_numbers(tree, result)
            self._check_dead_code(tree, code, result)
            self._check_missing_docstrings(tree, result)
            self._check_unnecessary_else(tree, result)
            self._check_broad_except(tree, result)
            self._check_variable_shadowing(tree, result)
            self._check_too_many_returns(tree, result)
            self._check_missing_init(tree, result)
            self._check_redundant_pass(tree, result)
        except SyntaxError:
            pass  # Already reported by security scanner

        self._check_todos(code, result)
        self._check_long_lines(code, result)
        self._check_duplicate_code(code, result)
        self._check_naming_conventions(code, result)

    # ── Cyclomatic complexity ──────────────────────────────────────────────

    def _check_complexity(self, tree: ast.AST, code: str, result: ScanResult) -> None:
        """Flag functions with high cyclomatic complexity."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                       ast.ExceptHandler, ast.With, ast.AsyncWith,
                                       ast.Assert)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1

            if complexity >= 15:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_HIGH,
                    title=f"Extremely complex function: {node.name}()",
                    description=f"Function '{node.name}()' has a cyclomatic complexity of {complexity} "
                                f"(recommended: < 10). This makes the code very hard to test, understand, "
                                f"and maintain — it likely contains hidden bugs.",
                    line_number=node.lineno,
                    snippet=code.splitlines()[node.lineno - 1].strip() if node.lineno else "",
                    recommendation=f"Break '{node.name}()' into smaller helper functions. Aim for "
                                   f"complexity under 10 per function.",
                    finding_type="quality",
                ))
            elif complexity >= 10:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_MEDIUM,
                    title=f"Complex function: {node.name}()",
                    description=f"Function '{node.name}()' has a cyclomatic complexity of {complexity}. "
                                f"It has a lot of branching logic (if/else/loops), which makes it "
                                f"hard to follow and test.",
                    line_number=node.lineno,
                    snippet=code.splitlines()[node.lineno - 1].strip() if node.lineno else "",
                    recommendation=f"Consider splitting '{node.name}()' into smaller functions.",
                    finding_type="quality",
                ))

    # ── Long functions ─────────────────────────────────────────────────────

    def _check_long_functions(self, tree: ast.AST, code: str, result: ScanResult) -> None:
        """Flag functions that exceed reasonable line counts."""
        lines = code.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.end_lineno or not node.lineno:
                continue
            func_lines = node.end_lineno - node.lineno + 1
            if func_lines > 100:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_HIGH,
                    title=f"Very long function: {node.name}() — {func_lines} lines",
                    description=f"Function '{node.name}()' is {func_lines} lines long. Functions over "
                                f"50-60 lines are hard to read, test, and maintain. Long functions "
                                f"often try to do too many things at once.",
                    line_number=node.lineno,
                    recommendation=f"Break '{node.name}()' into smaller focused functions, each "
                                   f"doing one thing.",
                    finding_type="quality",
                ))
            elif func_lines > 60:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_MEDIUM,
                    title=f"Long function: {node.name}() — {func_lines} lines",
                    description=f"Function '{node.name}()' is {func_lines} lines long. Consider "
                                f"splitting it into smaller pieces.",
                    line_number=node.lineno,
                    recommendation=f"Consider refactoring '{node.name}()' into smaller functions.",
                    finding_type="quality",
                ))

    # ── Empty exception handlers ───────────────────────────────────────────

    def _check_empty_handlers(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag bare except:pass or except Exception:pass."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            # Check if handler body is just "pass" or empty
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                type_name = ""
                if node.type is None:
                    type_name = "bare except"
                elif isinstance(node.type, ast.Name):
                    type_name = f"except {node.type.id}"
                elif isinstance(node.type, ast.Tuple):
                    type_name = "except (multiple)"

                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_HIGH if node.type is None else RISK_MEDIUM,
                    title=f"Empty {type_name}: handler silently swallows errors",
                    description=f"'{type_name}: pass' silently catches and discards all errors. "
                                f"This hides bugs and makes debugging extremely difficult. "
                                + ("" if node.type else " A bare `except:` also catches SystemExit "
                                  "and KeyboardInterrupt, which is almost never what you want."),
                    line_number=node.lineno,
                    snippet=f"except{'' if node.type is None else ' ' + type_name.split()[-1]}: pass"
                            if node.lineno else "",
                    recommendation="At minimum log the error with `logging.exception()`, or handle "
                                   "specific exceptions individually. Never silently swallow errors.",
                    finding_type="quality",
                ))

    # ── Too many parameters ────────────────────────────────────────────────

    def _check_too_many_params(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag functions with too many parameters."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            total = len(node.args.args) + len(node.args.kwonlyargs)
            if node.args.vararg:
                total += 1
            if node.args.kwarg:
                total += 1

            if total > 10:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_MEDIUM,
                    title=f"Too many parameters: {node.name}() — {total} params",
                    description=f"Function '{node.name}()' has {total} parameters. "
                                f"Functions with too many parameters are hard to call correctly "
                                f"and suggest missing abstractions.",
                    line_number=node.lineno,
                    recommendation=f"Group related parameters into a data class or use keyword-only "
                                   f"arguments. Consider splitting '{node.name}()' into smaller functions.",
                    finding_type="quality",
                ))

    # ── Unused variables ───────────────────────────────────────────────────

    def _check_unused_vars(self, tree: ast.AST, result: ScanResult) -> None:
        """Detect variables that are assigned but never used."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Collect all assignments (variable names)
            assigned: set[str] = set()
            # Collect all name references
            used: set[str] = set()
            # Skip 'self', 'cls', positional args, and kwargs
            skip_names = {'self', 'cls', '_'}
            # Add function parameters as "used" (they're inputs)
            for arg in node.args.args:
                skip_names.add(arg.arg)
            if node.args.vararg:
                skip_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                skip_names.add(node.args.kwarg.arg)

            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id not in skip_names:
                            assigned.add(target.id)
                elif isinstance(child, ast.AnnAssign):
                    if isinstance(child.target, ast.Name) and child.target.id not in skip_names:
                        assigned.add(child.target.id)
                elif isinstance(child, ast.Name):
                    if isinstance(child.ctx, ast.Load) and child.id not in skip_names:
                        used.add(child.id)

            unused = assigned - used
            for var in sorted(unused):
                # Only report variables used outside comprehensions — filter noisy patterns
                if var.startswith('_'):
                    continue  # Convention for unused
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_LOW,
                    title=f"Unused variable: '{var}'",
                    description=f"Variable '{var}' is assigned but never used in "
                                f"function '{node.name}()'. Unused variables create confusion "
                                f"and suggest incomplete code or leftover logic.",
                    recommendation=f"Remove '{var}' if it's not needed, or use it if the logic "
                                   f"is incomplete.",
                    finding_type="quality",
                ))

    # ── Deep nesting ───────────────────────────────────────────────────────

    def _check_nesting_depth(self, tree: ast.AST, code: str, result: ScanResult) -> None:
        """Flag deeply nested code blocks."""
        NESTING_TYPES = (ast.If, ast.While, ast.For, ast.AsyncFor,
                         ast.Try, ast.With, ast.AsyncWith)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            max_depth = 0
            # Walk body manually to track depth
            def walk_depth(n: ast.AST, depth: int) -> None:
                nonlocal max_depth
                if depth > max_depth:
                    max_depth = depth
                for child in ast.iter_child_nodes(n):
                    if isinstance(child, NESTING_TYPES):
                        walk_depth(child, depth + 1)
                    elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        pass  # Don't dive into nested functions
                    else:
                        walk_depth(child, depth)

            walk_depth(node, 0)
            if max_depth >= 6:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_HIGH,
                    title=f"Deeply nested code in '{node.name}()' — {max_depth} levels deep",
                    description=f"Function '{node.name}()' has code nested {max_depth} levels deep. "
                                f"Deep nesting makes code extremely hard to read and is a common "
                                f"source of logic errors.",
                    line_number=node.lineno,
                    recommendation="Use early returns, guard clauses, or extract inner blocks "
                                   "into separate functions to reduce nesting.",
                    finding_type="quality",
                ))
            elif max_depth >= 4:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_MEDIUM,
                    title=f"Nesting depth warning in '{node.name}()' — {max_depth} levels",
                    description=f"Function '{node.name}()' has code nested {max_depth} levels deep. "
                                f"This can be hard to follow.",
                    line_number=node.lineno,
                    recommendation="Consider using guard clauses or extracting inner logic "
                                   "into helper functions.",
                    finding_type="quality",
                ))

    # ── Magic numbers ──────────────────────────────────────────────────────

    def _check_magic_numbers(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag unexplained numeric literals (magic numbers)."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Collect assignments to named constants
            constants: set[int | float] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and isinstance(child.value, ast.Constant) \
                                and isinstance(child.value.value, (int, float)):
                            constants.add(child.value.value)
                        elif isinstance(target, ast.Attribute) and isinstance(child.value, ast.Constant) \
                                and isinstance(child.value.value, (int, float)):
                            constants.add(child.value.value)

            # Now find bare numeric literals that aren't 0, 1, -1, or named
            for child in ast.walk(node):
                if (isinstance(child, ast.Constant) and isinstance(child.value, (int, float))
                        and child.value not in {0, 1, -1, 0.0, 1.0, -1.0, 100, 60, 24, 3600}
                        and child.value not in constants
                        and not isinstance(getattr(child, 'parent', None), ast.Assign)):
                    line_num = getattr(child, 'lineno', None)
                    result.add(ScanFinding(
                        category="Code Quality",
                        risk_level=RISK_LOW,
                        title=f"Magic number: {child.value}",
                        description=f"The numeric literal `{child.value}` appears without explanation. "
                                    f"Magic numbers make code harder to understand and maintain.",
                        line_number=line_num,
                        recommendation=f"Assign `{child.value}` to a named constant with a descriptive "
                                       f"name (e.g., `MAX_RETRIES = {child.value}`).",
                        finding_type="quality",
                    ))
                    break  # One per function to avoid noise

    # ── Dead code ───────────────────────────────────────────────────────────

    def _check_dead_code(self, tree: ast.AST, code: str, result: ScanResult) -> None:
        """Detect code that follows return/raise/break/continue in the same block."""
        TERMINAL = (ast.Return, ast.Raise, ast.Break, ast.Continue)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.If, ast.Try, ast.For, ast.While)):
                continue
            body = node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else node.body
            for i, stmt in enumerate(body):
                if isinstance(stmt, TERMINAL):
                    # Check if there's code after this statement
                    for j in range(i + 1, len(body)):
                        # Skip docstrings
                        if isinstance(body[j], ast.Expr) and isinstance(body[j].value, ast.Constant):
                            continue
                        dead_line = getattr(body[j], 'lineno', None)
                        result.add(ScanFinding(
                            category="Code Quality",
                            risk_level=RISK_MEDIUM,
                            title="Dead code (unreachable)",
                            description=f"Code at line {dead_line} comes after a "
                                        f"'{type(stmt).__name__.lower()}' statement "
                                        f"at line {getattr(stmt, 'lineno', '?')}. "
                                        f"This code will never execute.",
                            line_number=dead_line,
                            snippet=code.splitlines()[dead_line - 1].strip() if dead_line and dead_line <= len(code.splitlines()) else "",
                            recommendation="Remove the unreachable code or restructure the logic.",
                            finding_type="quality",
                        ))
                    break  # Only report first dead block per parent

    # ── Missing docstrings ─────────────────────────────────────────────────

    def _check_missing_docstrings(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag public functions, classes, and modules without docstrings."""
        # Check module-level docstring
        if not isinstance(tree.body[0], ast.Expr) or not isinstance(tree.body[0].value, ast.Constant):
            pass  # Module docstring check is noisy for snippets

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    result.add(ScanFinding(
                        category="Code Quality",
                        risk_level=RISK_LOW,
                        title=f"Missing docstring for class '{node.name}'",
                        description=f"Class '{node.name}' has no docstring. Docstrings help others "
                                    f"(and your future self) understand what this class does.",
                        line_number=node.lineno,
                        recommendation=f"Add a docstring to '{node.name}' explaining its purpose.",
                        finding_type="quality",
                    ))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private methods, __init__, and overrides
                if node.name.startswith('__') and node.name.endswith('__'):
                    continue
                if node.name.startswith('_'):
                    continue
                if not ast.get_docstring(node):
                    result.add(ScanFinding(
                        category="Code Quality",
                        risk_level=RISK_LOW,
                        title=f"Missing docstring for function '{node.name}'",
                        description=f"Function '{node.name}()' has no docstring explaining what it does, "
                                    f"its parameters, or return value.",
                        line_number=node.lineno,
                        recommendation=f"Add a docstring to '{node.name}()' describing its purpose.",
                        finding_type="quality",
                    ))

    # ── Unnecessary else after return/raise/break/continue ─────────────────

    def _check_unnecessary_else(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag 'else' blocks after if-statements that always exit (return/raise/break)."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            # Check if body ends with return/raise/break/continue
            if node.body and isinstance(node.body[-1], (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                if node.orelse and not isinstance(node.orelse[0], ast.If):  # Not elif
                    line = node.orelse[0].lineno
                    snippet_lines = []
                    for child in node.orelse[:1]:
                        if hasattr(child, 'lineno') and child.lineno:
                            snippet_lines.append(str(child.lineno))
                    result.add(ScanFinding(
                        category="Code Quality",
                        risk_level=RISK_LOW,
                        title="Unnecessary 'else' after early return/raise",
                        description=f"The 'else' block starting at line {line} is unnecessary because "
                                    f"the 'if' block always exits (return/raise/break). Removing 'else' "
                                    f"and un-indenting the code makes it cleaner.",
                        line_number=line,
                        recommendation="Remove the 'else' and un-indent the else-block content.",
                        finding_type="quality",
                    ))

    # ── Bare / overly broad except ─────────────────────────────────────────

    def _check_broad_except(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag bare `except:` or `except Exception:` without specific handling."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if handler.type is None:
                    result.add(ScanFinding(
                        category="Code Quality",
                        risk_level=RISK_MEDIUM,
                        title="Bare 'except:' catches ALL exceptions",
                        description="A bare `except:` catches every possible exception including "
                                    "SystemExit and KeyboardInterrupt. This can make the program "
                                    "impossible to kill and hides critical errors.",
                        line_number=handler.lineno,
                        snippet="except:" if handler.lineno else "",
                        recommendation="Use a specific exception type (e.g., `except ValueError:`) "
                                       "or at minimum `except Exception:`.",
                        finding_type="quality",
                    ))

    # ── Variable shadowing ─────────────────────────────────────────────────

    def _check_variable_shadowing(self, tree: ast.AST, result: ScanResult) -> None:
        """Detect local variables that shadow built-in names or outer scope names."""
        BUILTINS = {'str', 'int', 'list', 'dict', 'tuple', 'set', 'bool', 'float',
                     'len', 'range', 'map', 'filter', 'type', 'object', 'print',
                     'input', 'open', 'file', 'dir', 'id', 'repr', 'all', 'any',
                     'sum', 'min', 'max', 'abs', 'sorted', 'reversed', 'enumerate',
                     'zip', 'iter', 'next', 'slice', 'property', 'staticmethod',
                     'classmethod', 'super', 'isinstance', 'hasattr', 'getattr',
                     'setattr', 'Exception', 'ValueError', 'TypeError', 'KeyError',
                     'FileNotFoundError', 'ImportError'}

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in ast.walk(node):
                # Check for loop variables
                if isinstance(child, ast.For):
                    if isinstance(child.target, ast.Name) and child.target.id in BUILTINS:
                        result.add(ScanFinding(
                            category="Code Quality",
                            risk_level=RISK_LOW,
                            title=f"Variable shadows built-in: '{child.target.id}'",
                            description=f"'{child.target.id}' is a Python built-in. Reassigning it "
                                        f"makes the actual built-in unavailable in this scope.",
                            line_number=child.lineno,
                            recommendation=f"Use a different name instead of '{child.target.id}'.",
                            finding_type="quality",
                        ))
                # Check for except ... as e
                elif isinstance(child, ast.ExceptHandler):
                    if isinstance(child.name, ast.Name) and child.name.id in BUILTINS:
                        result.add(ScanFinding(
                            category="Code Quality",
                            risk_level=RISK_LOW,
                            title=f"Variable shadows built-in: '{child.name.id}'",
                            description=f"'{child.name.id}' is a Python built-in. Using it as an "
                                        f"exception variable shadows the built-in.",
                            line_number=child.lineno,
                            recommendation=f"Use a different name like 'exc' or 'err' instead of "
                                           f"'{child.name.id}'.",
                            finding_type="quality",
                        ))

    # ── Too many return points ─────────────────────────────────────────────

    def _check_too_many_returns(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag functions with excessive return statements."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            returns = 0
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value is not None:
                    returns += 1
            if returns > 5:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_MEDIUM,
                    title=f"Too many return points: {node.name}() — {returns} returns",
                    description=f"Function '{node.name}()' has {returns} different return statements. "
                                f"Multiple exit points make the logic harder to follow and debug.",
                    line_number=node.lineno,
                    recommendation=f"Simplify '{node.name}()' by unifying return paths or splitting "
                                   f"into smaller functions.",
                    finding_type="quality",
                ))

    # ── Missing __init__ ───────────────────────────────────────────────────

    def _check_missing_init(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag classes without __init__ that have instance attributes."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            has_init = any(
                isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == '__init__'
                for m in node.body
            )
            has_methods = any(
                isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith('_')
                for m in node.body
            )
            if has_methods and not has_init:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_LOW,
                    title=f"Class '{node.name}' is missing __init__",
                    description=f"Class '{node.name}' has methods but no __init__ constructor. "
                                f"Without a constructor, instance attributes are created "
                                f"inconsistently across methods.",
                    line_number=node.lineno,
                    recommendation=f"Add an __init__ method to '{node.name}' that initializes "
                                   f"all instance attributes.",
                    finding_type="quality",
                ))

    # ── Redundant pass ─────────────────────────────────────────────────────

    def _check_redundant_pass(self, tree: ast.AST, result: ScanResult) -> None:
        """Flag 'pass' statements that appear with other statements in a body."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.If,
                                  ast.Try, ast.For, ast.AsyncFor, ast.While)):
                body = node.body if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                                       ast.AsyncFunctionDef)) else node.body
                if len(body) > 1:
                    for stmt in body:
                        if isinstance(stmt, ast.Pass):
                            result.add(ScanFinding(
                                category="Code Quality",
                                risk_level=RISK_INFO,
                                title="Redundant 'pass' statement",
                                description="A 'pass' statement appears alongside other code. "
                                            "'pass' is a no-op and should be removed when the body "
                                            "already has real statements.",
                                line_number=stmt.lineno,
                                recommendation="Remove the 'pass' statement.",
                                finding_type="quality",
                            ))

    # ── TODO/FIXME comments ────────────────────────────────────────────────

    def _check_todos(self, code: str, result: ScanResult) -> None:
        """Flag TODO, FIXME, HACK, XXX comments."""
        markers = [
            (r"(?i)#\s*(TODO)\b", "unfinished work"),
            (r"(?i)#\s*(FIXME)\b", "known bug or issue"),
            (r"(?i)#\s*(HACK)\b", "quick-and-dirty workaround"),
            (r"(?i)#\s*(XXX)\b", "notable concern"),
        ]
        for pattern, context in markers:
            for match in re.finditer(pattern, code):
                line_number = code[:match.start()].count("\n") + 1
                end_of_line = code.splitlines()[line_number - 1].strip() if line_number <= len(code.splitlines()) else ""
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_LOW,
                    title=f"{match.group(1).upper()} comment",
                    description=f"There's a '{match.group(1)}' comment in the code: "
                                f"\"{end_of_line[:80]}\". This indicates {context} that "
                                f"should be addressed.",
                    line_number=line_number,
                    snippet=end_of_line[:100],
                    recommendation=f"Address the {context} and remove the TODO comment.",
                    finding_type="quality",
                ))

    # ── Long lines ─────────────────────────────────────────────────────────

    def _check_long_lines(self, code: str, result: ScanResult) -> None:
        """Flag lines that exceed recommended length."""
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if len(stripped) > 120:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_INFO,
                    title=f"Very long line ({len(stripped)} chars)",
                    description=f"Line {i} is {len(stripped)} characters long. Very long lines "
                                f"require horizontal scrolling and are hard to read.",
                    line_number=i,
                    snippet=stripped[:120],
                    recommendation="Break this line into multiple lines using parentheses or "
                                   "continuation characters.",
                    finding_type="quality",
                ))
                break  # One is enough as a signal
            elif len(stripped) > 100:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_INFO,
                    title=f"Long line ({len(stripped)} chars)",
                    description=f"Line {i} is {len(stripped)} characters long. Consider breaking it up.",
                    line_number=i,
                    snippet=stripped[:120],
                    recommendation="Break long lines for better readability (limit to ~100 chars).",
                    finding_type="quality",
                ))
                break  # One is enough as a signal

    # ── Duplicate code blocks ──────────────────────────────────────────────

    def _check_duplicate_code(self, code: str, result: ScanResult) -> None:
        """
        Detect highly duplicated blocks of code (4+ identical lines appearing in
        multiple places). Uses line-level fingerprinting for robustness.
        """
        lines = [line.strip() for line in code.splitlines()]
        if len(lines) < 8:
            return

        # Build a map of line content -> list of line numbers
        line_map: dict[str, list[int]] = {}
        for i, line in enumerate(lines, 1):
            if line and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                line_map.setdefault(line, []).append(i)

        # Find blocks of 4+ consecutive duplicate lines
        duplicate_blocks: list[list[int]] = []
        seen_line_groups: set[tuple[int, ...]] = set()

        min_block = 4  # Minimum identical consecutive lines

        for i in range(len(lines) - min_block + 1):
            block = tuple(lines[i:i + min_block])
            if block in seen_line_groups:
                continue
            # Check if this block appears elsewhere
            for j in range(i + 1, len(lines) - min_block + 1):
                if tuple(lines[j:j + min_block]) == block:
                    seen_line_groups.add(block)
                    duplicate_blocks.append([i + 1, j + 1])
                    break

        for block in duplicate_blocks:
            result.add(ScanFinding(
                category="Code Quality",
                risk_level=RISK_MEDIUM,
                title="Duplicate code block detected",
                description=f"Lines {block[0]}-{block[0] + min_block - 1} appear to be duplicated "
                            f"at lines {block[1]}-{block[1] + min_block - 1}. Duplicate code "
                            f"means if you fix a bug in one place, you'll forget the other. "
                            f"It also makes the code longer than it needs to be.",
                line_number=block[0],
                snippet=lines[block[0] - 1][:80],
                recommendation="Extract the duplicated logic into a shared function and call it "
                               "from both places.",
                finding_type="quality",
            ))

    # ── Naming conventions ─────────────────────────────────────────────────

    def _check_naming_conventions(self, code: str, result: ScanResult) -> None:
        """Check for naming convention violations (snake_case, CamelCase)."""
        # Python conventions:
        #   - functions/variables: snake_case
        #   - classes: PascalCase
        #   - constants: UPPER_CASE
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Check class names
                if isinstance(node, ast.ClassDef):
                    if not re.match(r'^[A-Z][a-zA-Z0-9]+$', node.name):
                        if not node.name.startswith('_'):
                            result.add(ScanFinding(
                                category="Code Quality",
                                risk_level=RISK_INFO,
                                title=f"Class name should be PascalCase: '{node.name}'",
                                description=f"Class '{node.name}' does not follow Python's PascalCase "
                                            f"convention (e.g., 'MyClass', 'UserProfile').",
                                line_number=node.lineno,
                                recommendation=f"Rename '{node.name}' to follow PascalCase.",
                                finding_type="quality",
                            ))
                # Check function names
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith('__') and not node.name.startswith('_'):
                        if not re.match(r'^[a-z][a-z0-9_]*$', node.name):
                            result.add(ScanFinding(
                                category="Code Quality",
                                risk_level=RISK_INFO,
                                title=f"Function name should be snake_case: '{node.name}'",
                                description=f"Function '{node.name}()' does not follow Python's "
                                            f"snake_case convention (e.g., 'get_user', 'validate_input').",
                                line_number=node.lineno,
                                recommendation=f"Rename '{node.name}()' to follow snake_case.",
                                finding_type="quality",
                            ))
        except SyntaxError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# Security Scanner (existing, enhanced)
# ═══════════════════════════════════════════════════════════════════════════════

class PythonScanner:
    """Scans Python code using AST + regex patterns for security issues."""

    def scan(self, code: str) -> ScanResult:
        result = ScanResult("python", code)

        # 1. AST analysis — detect dangerous calls
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                self._check_ast_node(node, code, result)
        except SyntaxError as e:
            result.add(ScanFinding(
                category="Syntax",
                risk_level=RISK_INFO,
                title="Syntax Error in Code",
                description=f"The code has a syntax error: {e}. Analysis may be incomplete.",
                recommendation="Fix the syntax error first.",
            ))

        # 2. Regex-based pattern matching
        self._check_patterns(code, result)

        # 3. SQL injection check
        self._check_sql_injection(code, result)

        # 4. Code quality analysis
        quality = CodeQualityAnalyzer()
        quality.analyze(code, result)

        return result

    def _check_ast_node(self, node: ast.AST, code: str, result: ScanResult) -> None:
        """Walk AST for dangerous function calls."""
        if isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            if func_name and func_name in DANGEROUS_FUNCTIONS:
                line = getattr(node, "lineno", None)
                snippet = code.splitlines()[line - 1].strip() if line and line <= len(code.splitlines()) else ""
                risk = RISK_HIGH if any(func_name.startswith(p) for p in ("os.", "subprocess.")) else RISK_MEDIUM
                result.add(ScanFinding(
                    category="Dangerous Function",
                    risk_level=risk,
                    title=f"Dangerous function: {func_name}()",
                    description=DANGEROUS_FUNCTIONS[func_name],
                    line_number=line,
                    snippet=snippet,
                    recommendation=f"Replace {func_name}() with a safer alternative, or validate all inputs thoroughly.",
                    finding_type="security",
                ))

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Extract the full function name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            else:
                return None
            return ".".join(reversed(parts))
        return None

    def _check_patterns(self, code: str, result: ScanResult) -> None:
        """Check regex patterns for sensitive info leaks."""
        for pattern, risk_level, category, explanation in SENSITIVE_PATTERNS:
            for match in re.finditer(pattern, code):
                line_number = code[:match.start()].count("\n") + 1
                result.add(ScanFinding(
                    category=category,
                    risk_level=risk_level,
                    title=category,
                    description=explanation,
                    line_number=line_number,
                    snippet=match.group()[:120],
                    recommendation="Move sensitive values to environment variables (.env file).",
                    finding_type="security",
                ))

    def _check_sql_injection(self, code: str, result: ScanResult) -> None:
        """Detect potential SQL injection patterns."""
        for pattern in SQL_INJECTION_PATTERNS:
            for match in re.finditer(pattern, code):
                line_number = code[:match.start()].count("\n") + 1
                result.add(ScanFinding(
                    category="SQL Injection",
                    risk_level=RISK_HIGH,
                    title="Potential SQL Injection",
                    description="SQL query built with string concatenation or formatting. An attacker could manipulate the query.",
                    line_number=line_number,
                    snippet=match.group()[:150],
                    recommendation="Use parameterized queries (e.g., cursor.execute('SELECT * FROM t WHERE id = ?', (id,))) instead.",
                    finding_type="security",
                ))


class GenericScanner:
    """Scanners for non-Python languages (JS, Go, C++, etc.) using regex patterns."""

    LANGUAGE_EXTENSIONS = {
        "javascript": "js",
        "python3": "python",
        "go": "go",
        "cpp": "cpp",
    }

    # Cross-language dangerous patterns
    DANGEROUS_PATTERNS: dict[str, list[tuple[str, str, str, str]]] = {
        "javascript": [
            (r"eval\s*\(", RISK_CRITICAL, "eval() call", "eval() executes arbitrary JavaScript. Full XSS and code injection risk."),
            (r"new\s+Function\s*\(", RISK_HIGH, "Dynamic Function constructor", "Similar to eval — can execute arbitrary code."),
            (r"innerHTML\s*=", RISK_MEDIUM, "innerHTML assignment", "Can lead to XSS if content includes user data."),
            (r"document\.write\s*\(", RISK_MEDIUM, "document.write()", "Can lead to XSS injection."),
            (r"localStorage\s*\.\s*setItem", RISK_LOW, "localStorage write", "Sensitive data in localStorage is accessible via XSS."),
            (r"fetch\s*\(\s*['\"]https?://", RISK_MEDIUM, "Outbound fetch request", "Code makes network requests to external servers."),
            (r"XMLHttpRequest\s*\(", RISK_MEDIUM, "XMLHttpRequest", "Code makes AJAX requests. Verify the target is safe."),
            (r"require\s*\(\s*['\"]child_process['\"]\s*\)", RISK_HIGH, "child_process module", "Access to system processes from Node.js."),
            (r"require\s*\(\s*['\"]fs['\"]\s*\)", RISK_MEDIUM, "File system module", "Node.js filesystem access. Can read/write server files."),
            # JS-specific quality checks
            (r"(?i)console\.log\s*\(", RISK_INFO, "console.log()", "Debug logging left in production code."),
            (r"(?i)debugger\s*;?", RISK_MEDIUM, "debugger statement", "Debugger statement left in code — stops execution in devtools."),
            (r"(?i)//\s*(TODO|FIXME|HACK|XXX)", RISK_LOW, "TODO/FIXME/HACK comment", "Unfinished work or known issue left in code."),
            (r"(?i)var\s+", RISK_LOW, "'var' keyword used", "Prefer 'const' or 'let' over 'var' in modern JavaScript."),
        ],
        "go": [
            (r"exec\.Command\s*\(", RISK_HIGH, "exec.Command()", "Executes shell commands. Risk of command injection."),
            (r"os\.Exec\s*\(", RISK_HIGH, "os.Exec()", "Runs an external command — validate inputs."),
            (r"sql\.Open\s*\(", RISK_MEDIUM, "Database connection", "Connects to a database. Check credentials are not hardcoded."),
            (r"net\.Dial\s*\(", RISK_MEDIUM, "Network dial", "Opens a raw network connection. Check where it connects to."),
            (r"http\.Get\s*\(", RISK_MEDIUM, "HTTP GET", "Makes an HTTP request to an external server."),
            (r"os\.Remove\s*\(", RISK_MEDIUM, "os.Remove()", "Deletes a file — verify the path is correct."),
            (r"(?i)//\s*(TODO|FIXME|HACK|XXX)", RISK_LOW, "TODO/FIXME comment", "Unfinished work left in code."),
        ],
        "cpp": [
            (r"system\s*\(", RISK_CRITICAL, "system() call", "Executes shell commands. Full command injection risk."),
            (r"popen\s*\(", RISK_HIGH, "popen() call", "Opens a pipe to a shell command. Injection risk."),
            (r"(?i)ShellExecute\s*\(", RISK_HIGH, "ShellExecute()", "Windows ShellExecute — runs external programs."),
            (r"(?i)CreateProcess\s*\(", RISK_HIGH, "CreateProcess()", "Windows process creation — runs external programs."),
            (r"(?i)WinExec\s*\(", RISK_HIGH, "WinExec()", "Windows process execution — runs external programs."),
            (r"(?i)malloc\s*\(.*sizeof.*\)", RISK_LOW, "Manual memory allocation", "Risk of memory leak if not freed properly."),
            (r"(?i)free\s*\(", RISK_INFO, "Memory deallocation", "Check that pointers are not used after free."),
            (r"(?i)strcpy\s*\(", RISK_HIGH, "strcpy() — buffer overflow risk", "No bounds checking. Use strncpy or safer alternatives."),
            (r"(?i)strcat\s*\(", RISK_HIGH, "strcat() — buffer overflow risk", "No bounds checking. Use strncat or safer alternatives."),
            (r"(?i)gets\s*\(", RISK_CRITICAL, "gets() — buffer overflow", "gets() has no bounds checking. Use fgets() instead."),
            (r"(?i)scanf\s*\(['\"]%s", RISK_MEDIUM, "scanf %s — buffer overflow risk", "Unbounded string input can overflow the buffer."),
            (r"(?i)#include\s*<iostream>", RISK_INFO, "C++ I/O", "Standard C++ input/output. No specific risk."),
            (r"(?i)//\s*(TODO|FIXME|HACK|XXX)", RISK_LOW, "TODO/FIXME comment", "Unfinished work left in code."),
        ],
    }

    # Generic quality checks applicable to any language
    GENERIC_QUALITY_PATTERNS: list[tuple[str, str, str, str]] = [
        (r"(?i)//\s*(TODO|FIXME|HACK|XXX)", RISK_LOW, "Unfinished work marker",
         "A TODO/FIXME/HACK comment suggests this code has unfinished work or known issues."),
        (r"(?i)\bdebugger\s*;?", RISK_MEDIUM, "Debugger statement",
         "A debugger statement will pause execution in development tools."),
        (r"(?i)console\.log\s*\(", RISK_INFO, "Console log left in code",
         "Debug console.log() statements should be removed from production code."),
    ]

    def scan(self, language: str, code: str) -> ScanResult:
        result = ScanResult(language, code)
        patterns = self.DANGEROUS_PATTERNS.get(language, [])

        for pattern, risk_level, title, description in patterns:
            for match in re.finditer(pattern, code):
                line_number = code[:match.start()].count("\n") + 1
                result.add(ScanFinding(
                    category="Dangerous Pattern",
                    risk_level=risk_level,
                    title=title,
                    description=description,
                    line_number=line_number,
                    snippet=match.group()[:120],
                    recommendation=f"Review the use of {title}. Use safer alternatives where possible.",
                    finding_type="security",
                ))

        # Generic pattern checks for all languages
        self._check_generic(code, result)

        return result

    def _check_generic(self, code: str, result: ScanResult) -> None:
        """Generic checks applicable to any language."""
        # Hardcoded secrets
        for pattern, risk_level, category, explanation in SENSITIVE_PATTERNS:
            for match in re.finditer(pattern, code):
                line_number = code[:match.start()].count("\n") + 1
                result.add(ScanFinding(
                    category=category,
                    risk_level=risk_level,
                    title=category,
                    description=explanation,
                    line_number=line_number,
                    snippet=match.group()[:120],
                    recommendation="Move sensitive values to environment variables or a secrets manager.",
                    finding_type="security",
                ))

        # Generic quality markers (for non-Python languages that don't get the full QA)
        for pattern, risk_level, title, description in self.GENERIC_QUALITY_PATTERNS:
            for match in re.finditer(pattern, code):
                line_number = code[:match.start()].count("\n") + 1
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=risk_level,
                    title=title,
                    description=description,
                    line_number=line_number,
                    snippet=match.group()[:120],
                    recommendation="Address this before deploying to production.",
                    finding_type="quality",
                ))

    # ═══════════════════════════════════════════════════════════════════════
    # Common utility checks that apply across all languages
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def detect_long_lines(code: str, result: ScanResult) -> None:
        """Check for overly long lines (language-agnostic)."""
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if len(stripped) > 120:
                result.add(ScanFinding(
                    category="Code Quality",
                    risk_level=RISK_INFO,
                    title=f"Very long line ({len(stripped)} chars)",
                    description=f"Line {i} is {len(stripped)} characters long.",
                    line_number=i,
                    recommendation="Break this into multiple lines for readability.",
                    finding_type="quality",
                ))
                break


# ═══════════════════════════════════════════════════════════════════════════════
# Main scanner dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

def scan_code(language: str, code: str) -> ScanResult:
    """
    Scan source code for security issues AND code quality problems.

    Args:
        language: One of "python", "javascript", "go", "cpp"
        code: The source code to scan

    Returns:
        ScanResult with all findings (security + quality)
    """
    if not code.strip():
        result = ScanResult(language, code)
        result.add(ScanFinding(
            category="Empty Code",
            risk_level=RISK_INFO,
            title="Empty Code",
            description="The code is empty — nothing to scan.",
        ))
        return result

    if language == "python":
        scanner = PythonScanner()
        return scanner.scan(code)

    scanner = GenericScanner()
    return scanner.scan(language, code)
