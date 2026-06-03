"""
TruffleKit 扫描规则库
====================
每条规则包含：
  - id:        规则编号 (SEC-XXX)
  - category:  分类
  - severity:  严重等级 (critical/high/medium/low/info)
  - title:     标题
  - description: 问题描述
  - recommendation: 修复建议
  - reference: 参考链接 (OWASP/CVE/官方文档)
  - check:     检测函数 (接收 project_root Path, 返回 findings list)
"""

import os
import re
import stat as stat_module
import subprocess
from pathlib import Path
from collections import defaultdict

# ── 共用工具 ──────────────────────────────────────────────────────

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
    ".claude", "build", "dist", "target", "out", ".next",
    ".nuxt", ".cache", "vendor", ".bundle", "bin", "obj",
    ".gradle", ".idea", ".vscode", ".DS_Store", ".sass-cache",
    "coverage", ".nyc_output", "jspm_packages", "bower_components",
    "elm-stuff", ".stack-work", "deps", "_build", ".elixir_ls",
    "site-packages", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "Pods", ".build", "DerivedData", "migrations",
    "demo",          # 刻意包含不安全代码的 demo 目录
    "yizhizhu",      # 用户个人笔记（可能含示例密码）
    "legacy_backup", # 备份目录
    "Truffle",       # 项目内嵌的完整备份副本（避免重复扫描）
}

SKIP_FILE_EXT = {
    ".pyc", ".pyo", ".so", ".o", ".a", ".lib", ".dll", ".dylib",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".avi", ".mov", ".mkv",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".msi", ".db", ".sqlite", ".sqlite3",
    ".db-wal", ".db-shm",  # SQLite WAL 二进制文件
    ".log", ".bak", ".swp",
}


def _walk(root: Path):
    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        yield root_dir, dirs, files


def _rglob(root: Path, pattern: str):
    for f in root.rglob(pattern):
        if any(p in f.parts for p in SKIP_DIRS):
            continue
        yield f


def _fread(fp: Path) -> str | None:
    try:
        return fp.read_text(errors="ignore")
    except Exception:
        return None


def _rel(fp: Path, root: Path) -> str:
    try:
        return str(fp.relative_to(root))
    except ValueError:
        return str(fp)


# ── 规则注册 ──────────────────────────────────────────────────────

RULES = []
RULE_MAP = {}  # id -> rule


def register(id_, category, severity, title, description, recommendation, reference):
    """装饰器：注册一条规则"""
    def deco(check_fn):
        rule = {
            "id": id_,
            "category": category,
            "severity": severity,
            "title": title,
            "description": description,
            "recommendation": recommendation,
            "reference": reference,
            "check": check_fn,
        }
        RULES.append(rule)
        RULE_MAP[id_] = rule
        return check_fn
    return deco


def make_finding(file, line, snippet, severity=None, certainty="high", rule_id=None):
    """创建一条标准化的发现记录"""
    return {
        "file": file,
        "line": line,
        "snippet": str(snippet)[:120],
        "severity": severity,
        "certainty": certainty,
        "rule_id": rule_id,
    }


# ══════════════════════════════════════════════════════════════════
# SEC-001: 硬编码 API Key / Secret
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-001", "Secret Leak", "critical",
    "API Key / Secret 硬编码在源码中",
    "代码中直接写死了 API Key、密码、Token 等敏感信息。任何能看到代码的人都能窃取这些凭据，"
    "即使仓库是 private，所有有权限的人都能读到。",
    "1) 立即可轮换已泄露的密钥 2) 移到 .env 文件 3) 通过 os.getenv() 读取",
    "OWASP A02:2021 – Cryptographic Failures\nhttps://owasp.org/Top10/A02_2021-Cryptographic_Failures/"
)
def check_hardcoded_secrets(root: Path):
    issues = []
    patterns = [
        (r"(?i)sk_live_[A-Za-z0-9]+", "critical", "Stripe Live Key"),
        (r"(?i)pk_live_[A-Za-z0-9]+", "high", "Stripe Live Publishable Key"),
        (r"AKIA[0-9A-Z]{16}", "critical", "AWS Access Key"),
        (r"(?i)ghp_[A-Za-z0-9]{36}", "critical", "GitHub Token"),
        (r"(?i)gho_[A-Za-z0-9]{36}", "critical", "GitHub OAuth Token"),
        (r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "high", "JWT Token (疑似生产)"),
        (r"(?i)-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "critical", "Private Key"),
        (r"(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "high", "硬编码 API Key"),
        (r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{6,})['\"]", "critical", "硬编码密码"),
        (r"(?i)SECRET_KEY\s*[=:]\s*['\"]([^'\"]{8,})['\"]", "critical", "加密密钥硬编码"),
    ]

    for root_dir, dirs, files in _walk(root):
        for f in files:
            if f in (".env", ".env.example", ".env.local"):
                continue
            fp = Path(root_dir) / f
            ext = os.path.splitext(f)[1].lower()
            if ext in SKIP_FILE_EXT:
                continue
            content = _fread(fp)
            if not content:
                continue
            for pat, sev, label in patterns:
                for m in re.finditer(pat, content):
                    ln = content[:m.start()].count("\n") + 1
                    line_text = content.splitlines()[ln - 1] if ln <= len(content.splitlines()) else ""
                    # 在测试文件中跳过 test/example 密码
                    if "password" in label.lower() and "test" in str(fp).lower():
                        if re.search(r"(test|fake|example|placeholder|dummy|your-|YOUR_)", line_text, re.I):
                            continue
                    issues.append(make_finding(
                        _rel(fp, root), ln, m.group()[:60],
                        severity=sev, rule_id="SEC-001",
                    ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-002: .env 文件泄露风险
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-002", "Secret Leak", "high",
    ".env 文件可能被提交到 Git",
    ".env 文件包含环境变量/密钥，如果被 Git 跟踪并推送就会泄露。"
    "即使现在没有推送，也容易意外提交。",
    "1) 把 .env 加入 .gitignore 2) 创建 .env.example 做模板 3) 检查 Git 历史是否已有提交记录",
    "OWASP A02:2021 – Cryptographic Failures\nhttps://owasp.org/Top10/A02_2021-Cryptographic_Failures/"
)
def check_env_git(root: Path):
    issues = []
    env_file = root / ".env"
    if not env_file.exists():
        return issues

    gi = root / ".gitignore"
    if gi.exists():
        content = _fread(gi)
        if content and (".env" in content or ".env*" in content):
            return issues

    if (root / ".git").exists():
        try:
            r = subprocess.run(
                ["git", "-C", str(root), "ls-files", ".env"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                issues.append(make_finding(
                    ".env", 1, ".env 已经被 Git 跟踪！`git rm --cached .env` 之后再推送",
                    severity="critical", rule_id="SEC-002",
                ))
            else:
                issues.append(make_finding(
                    ".gitignore", 1, ".env 文件存在但未被 .gitignore 保护——有意外提交风险",
                    severity="high", rule_id="SEC-002",
                ))
        except Exception:
            issues.append(make_finding(
                ".env", 1, ".env 文件存在，但无法检查 Git 状态",
                severity="medium", rule_id="SEC-002",
            ))
    else:
        issues.append(make_finding(
            ".gitignore", 1, ".env 文件存在但项目没有 .gitignore，建议创建",
            severity="medium", rule_id="SEC-002",
        ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-003: Git 历史泄露敏感文件
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-003", "Git Leak", "high",
    "Git 历史中曾提交过敏感文件",
    "即使现在删除了 .env 或密钥文件，Git 历史里仍然可以找回。这是最常见的泄露途径——"
    "攻击者会查看项目的 commit 历史来找寻被遗忘的密钥。",
    "用 git filter-branch 或 BFG Repo-Cleaner 从全部历史中擦除敏感文件痕迹",
    "BFG Repo-Cleaner\nhttps://rtyley.github.io/bfg-repo-cleaner/"
)
def check_git_history(root: Path):
    issues = []
    if not (root / ".git").exists():
        return issues

    patterns = [".env", "*.key", "*.pem", "*.crt"]
    try:
        for pat in patterns:
            r = subprocess.run(
                ["git", "-C", str(root), "log", "--diff-filter=A", "--follow",
                 "--name-only", "--pretty=format:", "--", pat],
                capture_output=True, text=True, timeout=10
            )
            if r.stdout.strip():
                files = set(f.strip() for f in r.stdout.strip().split("\n") if f.strip())
                if files:
                    issues.append(make_finding(
                        "(git-history)", 1,
                        f"曾提交过: {', '.join(sorted(files)[:5])}。使用 BFG 从历史中清除",
                        severity="high", rule_id="SEC-003",
                    ))
    except Exception:
        pass
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-004: .gitignore 不完整
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-004", "Git Leak", "medium",
    ".gitignore 缺少关键规则",
    ".gitignore 没有保护常见敏感文件类型，容易意外提交密钥或构建产物。",
    "添加规则: .env, *.key, *.log, node_modules/, __pycache__/, *.db, dist/, build/",
    "Git 官方 .gitignore 模板\nhttps://github.com/github/gitignore"
)
def check_gitignore(root: Path):
    issues = []
    gi = root / ".gitignore"
    if not gi.exists():
        issues.append(make_finding(
            ".gitignore", 1, "项目没有 .gitignore 文件！",
            severity="high", rule_id="SEC-004",
        ))
        return issues

    content = _fread(gi) or ""
    essentials = [".env", "node_modules", "__pycache__", "*.key"]
    for e in essentials:
        if e not in content:
            issues.append(make_finding(
                ".gitignore", 1, f"缺少 '{e}' — 建议添加",
                severity="medium", rule_id="SEC-004",
            ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-005: SSL 私钥在项目目录
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-005", "SSL Certificate", "critical",
    "SSL 私钥文件在项目目录中",
    "SSL 私钥不应该存放在项目目录中。如果在 Git 仓库里，等于 HTTPS 保护完全失效。"
    "任何有仓库访问权限的人都能解密你的流量。",
    "1) 移出项目目录 2) 用 Let's Encrypt 或云服务商管理证书 3) *.key 加入 .gitignore",
    "Let's Encrypt\nhttps://letsencrypt.org/"
)
def check_ssl_keys(root: Path):
    issues = []
    for f in _rglob(root, "*.key"):
        if ".git" in f.parts:
            continue
        content = _fread(f)
        if content and "PRIVATE KEY" in content:
            issues.append(make_finding(
                _rel(f, root), 1, "SSL 私钥文件在项目目录中",
                severity="critical", rule_id="SEC-005",
            ))
        elif any(p in str(f).lower() for p in ["deploy", "ssl", "cert", "tls"]):
            issues.append(make_finding(
                _rel(f, root), 1, "密钥文件在项目目录中",
                severity="high", rule_id="SEC-005",
            ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-006: 生产代码残留调试语句
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-006", "Debug Artifact", "medium",
    "生产代码中残留了调试输出语句",
    "print() / console.log() 等在线上环境可能泄露敏感信息（如 SQL 查询、用户数据）或降低性能。"
    "也可能让代码看起来不专业。",
    "上线前全局搜索并清理调试输出，改用 logging 框架。保留必要的日志输出。",
    "OWASP A03:2021 – Injection\nhttps://owasp.org/Top10/A03_2021-Injection/"
)
def check_debug_stmts(root: Path):
    issues = []
    patterns = {
        ".py": [(r'^\s*print\s*\(', "print()")],
        ".js": [(r'console\.(log|debug|info|warn)\s*\(', "console.xxx()"), (r'debugger\s*;?', "debugger")],
        ".ts": [(r'console\.(log|debug|info|warn)\s*\(', "console.xxx()"), (r'debugger\s*;?', "debugger")],
        ".jsx": [(r'console\.(log|debug|info|warn)\s*\(', "console.xxx()")],
        ".tsx": [(r'console\.(log|debug|info|warn)\s*\(', "console.xxx()")],
        ".go": [(r'fmt\.(Print|Printf|Println)\s*\(', "fmt.Print()")],
        ".java": [(r'System\.out\.(print|println|printf)\s*\(', "System.out.print()")],
        ".php": [(r'(?:echo|var_dump|print_r)\s*\(', "echo/var_dump()")],
        ".rb": [(r'^\s*(p|puts|pp|print)\s', "p/puts/print()")],
    }

    count_by_ext = defaultdict(int)
    for root_dir, dirs, files in _walk(root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in patterns:
                continue
            fp = Path(root_dir) / f
            content = _fread(fp)
            if not content:
                continue
            for pat, label in patterns[ext]:
                for m in re.finditer(pat, content, re.MULTILINE):
                    ln = content[:m.start()].count("\n") + 1
                    if ln == 1 and f == "__init__.py":
                        continue
                    count_by_ext[ext] += 1
                    if count_by_ext[ext] <= 3:
                        issues.append(make_finding(
                            _rel(fp, root), ln, f"{label} — {m.group().strip()[:60]}",
                            severity="medium", rule_id="SEC-006",
                        ))

    if sum(count_by_ext.values()) > 3:
        total = sum(count_by_ext.values())
        issues.append(make_finding(
            "(project-wide)", 1, f"合计 {total} 条调试语句残留（已显示部分）",
            severity="medium", rule_id="SEC-006",
        ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-007: TODO/FIXME 累计
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-007", "Code Marker", "low",
    "TODO/FIXME/HACK 标记累计",
    "代码中的 TODO/FIXME 标记代表已知但未处理的遗留问题。每个标记意味着某个功能/边界情况/"
    "已知 bug 还没有解决。",
    "每个上线前过一遍 TODO 列表，决定是处理还是排期到下一个版本",
    "无特定参考 — 开发流程最佳实践"
)
def check_todos(root: Path):
    issues = []
    todos = []
    marker_pat = re.compile(r'(?i)(TODO|FIXME|HACK|XXX|BUG|WORKAROUND)\b')
    code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
                 ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
                 ".kt", ".sh", ".bash", ".yaml", ".yml", ".json", ".toml",
                 ".sql", ".lua", ".pl", ".pm", ".r", ".dart"}

    for root_dir, dirs, files in _walk(root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in code_exts:
                continue
            fp = Path(root_dir) / f
            content = _fread(fp)
            if not content:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                m = marker_pat.search(line)
                if m:
                    if not line.strip().startswith(("// TODO", "# TODO", "<!-- TODO")):
                        todos.append({"file": _rel(fp, root), "line": i, "marker": m.group(1).upper(), "text": line.strip()[:80]})

    if len(todos) > 3:
        issues.append(make_finding(
            "(project-wide)", 1, f"总计 {len(todos)} 个标记（TODO/FIXME/HACK）",
            severity="low", rule_id="SEC-007",
        ))
        for t in sorted(todos, key=lambda x: x["marker"])[:5]:
            issues.append(make_finding(
                t["file"], t["line"], f"[{t['marker']}] {t['text'][:60]}",
                severity="info", rule_id="SEC-007",
            ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-008: 敏感文件权限过于宽松
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-008", "File Permission", "medium",
    "敏感文件权限过于宽松",
    "密钥文件如果权限是 644（所有人可读），同一台机器的其他用户或进程能读到这些敏感信息。"
    "在多用户服务器上尤其危险。",
    "chmod 600 .env  &&  chmod 600 *.key",
    "Linux 文件权限基础\nhttps://www.gnu.org/software/coreutils/manual/html_node/File-permissions.html"
)
def check_perms(root: Path):
    issues = []
    sensitive = {".env", ".env.local", ".env.production", ".env.development"}
    for root_dir, dirs, files in _walk(root):
        for f in files:
            if f not in sensitive and not f.endswith((".key", ".pem", ".p12")):
                continue
            fp = Path(root_dir) / f
            try:
                mode = os.stat(fp).st_mode
                if mode & stat_module.S_IROTH:
                    perms = oct(mode & 0o777)
                    issues.append(make_finding(
                        _rel(fp, root), 1, f"权限 {perms} — 其他用户可读取，建议 chmod 600",
                        severity="medium", rule_id="SEC-008",
                    ))
            except Exception:
                pass
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-009: 硬编码绝对路径
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-009", "Hardcoded Path", "medium",
    "硬编码了本地绝对路径",
    "代码中的绝对路径（/home/xxx, /Users/xxx）在别的机器上会失效。"
    "部署到服务器或其他开发者机器上时会报错。",
    "用相对路径或环境变量替代，如 os.getenv('HOME') 或 pathlib 动态获取",
    "Python pathlib 文档\nhttps://docs.python.org/3/library/pathlib.html"
)
def check_hardcoded_paths(root: Path):
    issues = []
    pat = re.compile(r"""['"](/[a-zA-Z0-9_/.\-]+)['"]""")
    suspicious_prefix = ["/home/", "/Users/", "/tmp/", "/var/", "/etc/", "/opt/"]
    ok_prefixes = ["/usr/lib", "/usr/share", "/usr/include", "/etc/ssl"]

    for root_dir, dirs, files in _walk(root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".py", ".js", ".ts", ".sh", ".jsx", ".tsx", ".go",
                           ".rs", ".java", ".c", ".cpp", ".h", ".yaml", ".yml",
                           ".json", ".toml", ".rb", ".php", ".pl", ".kt",
                           ".swift", ".cs", ".lua"):
                continue
            fp = Path(root_dir) / f
            content = _fread(fp)
            if not content:
                continue
            for m in pat.finditer(content):
                path = m.group(1)
                is_suspicious = any(path.startswith(p) for p in suspicious_prefix)
                is_ok = any(path.startswith(p) for p in ok_prefixes)
                if is_suspicious and not is_ok:
                    ln = content[:m.start()].count("\n") + 1
                    issues.append(make_finding(
                        _rel(fp, root), ln, path[:80],
                        severity="medium", rule_id="SEC-009",
                    ))
                    break
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-010: 数据库文件暴露
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-010", "Database", "high",
    "数据库文件在项目目录中，可能被下载",
    "SQLite 数据库文件如果在 Web 根目录或项目目录中，浏览器可以直接下载完整数据库。"
    "攻击者拿到 .db 文件就等于拿到了你全部数据。",
    "把数据库移到 Web 根目录之外，或确保 nginx/apache 禁止访问 .db 文件",
    "OWASP A01:2021 – Broken Access Control\nhttps://owasp.org/Top10/A01_2021-Broken-Access-Control/"
)
def check_db_files(root: Path):
    issues = []
    for ext in ["*.db", "*.sqlite3", "*.sqlite"]:
        for f in _rglob(root, ext):
            if ".git" in f.parts:
                continue
            size = f.stat().st_size if f.exists() else 0
            if size > 1000:
                issues.append(make_finding(
                    _rel(f, root), 1, f"SQLite 数据库 ({size // 1024}KB) — 确保不可通过 Web 访问",
                    severity="high", rule_id="SEC-010",
                ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-011: 大文件
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-011", "Large File", "low",
    "项目中有大文件（>1MB）",
    "大文件不适合放在 Git 仓库，会拖慢 clone 和 pull。通常是构建产物、二进制文件或不该提交的。",
    "用 git-lfs 管理大文件，或从仓库中移除构建产物，通过 .gitignore 排除",
    "Git LFS\nhttps://git-lfs.com/"
)
def check_large_files(root: Path):
    issues = []
    count = 0
    skip_ext = {".mp4", ".mp3", ".avi", ".mov", ".mkv", ".pdf", ".zip", ".tar",
                ".gz", ".bz2", ".7z", ".rar", ".iso", ".dmg", ".exe", ".msi",
                ".dll", ".so", ".dylib", ".png", ".jpg", ".jpeg", ".gif", ".ico",
                ".woff", ".woff2", ".ttf", ".eot", ".otf", ".svg"}
    for root_dir, dirs, files in _walk(root):
        for f in files:
            fp = Path(root_dir) / f
            ext = os.path.splitext(f)[1].lower()
            try:
                size = fp.stat().st_size
                if size > 1_000_000 and ext not in skip_ext:
                    issues.append(make_finding(
                        _rel(fp, root), 1, f"{size // 1024 // 1024}MB — 考虑用 git-lfs 或从仓库移除",
                        severity="low", rule_id="SEC-011",
                    ))
                    count += 1
                    if count >= 5:
                        break
            except Exception:
                pass
        if count >= 5:
            break
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-012: Docker 端口暴露
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-012", "Docker", "medium",
    "Docker Compose 暴露了端口到公网",
    "Docker Compose 中的 ports 如果只写了端口号（如 8000:8000），默认绑定到 0.0.0.0，"
    "意味着任何人能访问。调试端口如果暴露到公网是严重的安全问题。",
    "用 127.0.0.1:8000:8000 代替 8000:8000 来限制本地访问",
    "Docker 安全最佳实践\nhttps://docs.docker.com/develop/security-best-practices/"
)
def check_docker_ports(root: Path):
    issues = []
    for f in _rglob(root, "docker-compose.yml"):
        content = _fread(f)
        if not content:
            continue
        in_ports = False
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if "ports:" in stripped:
                in_ports = True
                continue
            if in_ports and stripped.startswith("- "):
                if re.match(r'^-\s+"?\d+:\d+"?', stripped):
                    issues.append(make_finding(
                        _rel(f, root), i, stripped[:60],
                        severity="medium", rule_id="SEC-012",
                    ))
            elif in_ports and not stripped.startswith("- ") and not stripped.startswith("#"):
                in_ports = False
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-013: Docker 使用 latest 标签
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-013", "Docker", "low",
    "Docker 镜像用了 latest 标签",
    "':latest' 标签不固定版本，每次拉取可能得到不同版本。"
    "这会导致「在我机器上能跑，但在服务器上不行」的问题，且可能有破坏性更新。",
    "使用具体版本号标签，如 python:3.11-slim 而不是 python:latest",
    "Docker 标签最佳实践\nhttps://docs.docker.com/engine/reference/commandline/tag/"
)
def check_docker_latest(root: Path):
    issues = []
    for f in list(_rglob(root, "Dockerfile")) + list(_rglob(root, "Dockerfile.*")):
        content = _fread(f)
        if not content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if re.match(r'^FROM\s+\S+:latest\b', line, re.I):
                issues.append(make_finding(
                    _rel(f, root), i, line.strip()[:60],
                    severity="low", rule_id="SEC-013",
                ))
                break
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-014: 未固定依赖版本
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-014", "Dependency", "medium",
    "依赖没有固定版本号",
    "使用 >= 或无版本号会让每次安装得到不同版本。可能引入破坏性变更或已知有漏洞的版本，"
    "导致「在我机器上能跑」的经典问题。",
    "锁定到确切版本号，如 fastapi==0.115.0 而不是 fastapi>=0.115.0",
    "OWASP A06:2021 – Vulnerable and Outdated Components\nhttps://owasp.org/Top10/A06_2021-Vulnerable-and-Outdated-Components/"
)
def check_unpinned_deps(root: Path):
    issues = []

    for f in _rglob(root, "requirements.txt"):
        content = _fread(f)
        if not content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("-"):
                if ">=" in s or "<=" in s or "==" not in s:
                    issues.append(make_finding(
                        _rel(f, root), i, s[:60],
                        severity="medium", rule_id="SEC-014",
                    ))

    for f in _rglob(root, "package.json"):
        content = _fread(f)
        if not content:
            continue
        for pat in [r'"\^[\d.]+"', r'"~[\d.]+"']:
            for m in re.finditer(pat, content):
                if m:
                    ln = content[:m.start()].count("\n") + 1
                    issues.append(make_finding(
                        _rel(f, root), ln, m.group()[:60],
                        severity="medium", rule_id="SEC-014",
                    ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-015: 空 except / catch 块
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-015", "Error Handling", "medium",
    "空的异常捕获块（静默吞掉错误）",
    "catch/except 块为空或只有 pass，错误被静默吞掉。这会让程序在出错时毫无提示地继续运行，"
    "产生难以调试的 bug，甚至让安全机制失效。",
    "至少记录异常日志: 用 logging.exception() 捕获并记录",
    "OWASP A05:2021 – Security Misconfiguration\nhttps://owasp.org/Top10/A05_2021-Security-Misconfiguration/"
)
def check_empty_catch(root: Path):
    issues = []
    for root_dir, dirs, files in _walk(root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".py", ".js", ".ts", ".java", ".cpp"):
                continue
            fp = Path(root_dir) / f
            content = _fread(fp)
            if not content:
                continue
            lines = content.splitlines()

            if ext == ".py":
                for i, line in enumerate(lines):
                    if re.match(r'^\s*except\s*:', line) or re.match(r'^\s*except\s+\S+:', line):
                        for j in range(i + 1, min(i + 3, len(lines))):
                            if re.match(r'^\s*pass\s*$', lines[j]):
                                issues.append(make_finding(
                                    _rel(fp, root), i + 1, line.strip()[:60],
                                    severity="medium", rule_id="SEC-015",
                                ))
                            break
            elif ext in (".js", ".ts"):
                for i, line in enumerate(lines):
                    if re.search(r'catch\s*\([^)]*\)\s*\{\s*\}', line):
                        issues.append(make_finding(
                            _rel(fp, root), i + 1, line.strip()[:60],
                            severity="medium", rule_id="SEC-015",
                        ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-016: 缺少 README
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-016", "Documentation", "low",
    "项目没有 README 文件",
    "没有 README 会让新来的开发者/协作者不知道这个项目是做什么的、怎么跑起来。"
    "开源项目没有 README 基本等于不欢迎贡献者。",
    "创建一个 README.md，说明项目用途、安装方式、使用方法",
    "Make a README — 如何写好 README\nhttps://www.makeareadme.com/"
)
def check_readme(root: Path):
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        if (root / name).exists():
            return []
    return [make_finding("README.md", 1, "项目缺少 README", severity="low", rule_id="SEC-016")]


# ══════════════════════════════════════════════════════════════════
# SEC-017: 缺少 LICENSE
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-017", "Documentation", "low",
    "项目没有明确的 License（许可证）",
    "没有 LICENSE 文件意味着默认 All Rights Reserved——别人在法律上不敢用、改、分发你的代码。"
    "这会大大限制你的项目被采用的可能性。",
    "添加 LICENSE 文件，选择 MIT / Apache-2.0 / GPL-3.0 等适合的开源协议",
    "Choose a License\nhttps://choosealicense.com/"
)
def check_license(root: Path):
    license_names = {"LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"}
    has_license = any((root / n).exists() for n in license_names)
    if not has_license:
        return [make_finding("LICENSE", 1, "没有 License 文件", severity="low", rule_id="SEC-017")]
    return []


# ══════════════════════════════════════════════════════════════════
# SEC-018: 缺少 CI/CD 配置
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-018", "CI/CD", "info",
    "项目没有 CI/CD 配置",
    "没有 CI/CD 意味着每次代码变更都需要手动测试和部署，容易出现人为失误。"
    "虽然不是安全问题，但建议设置基础 CI。",
    "配置 GitHub Actions / GitLab CI / Jenkins 实现自动化测试和部署",
    "GitHub Actions\nhttps://docs.github.com/en/actions"
)
def check_ci_config(root: Path):
    ci_files = [".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml",
                 ".travis.yml", "Jenkinsfile", ".drone.yml"]
    has_ci = any((root / f).exists() for f in ci_files)
    if not has_ci:
        return [make_finding(".github/", 1, "项目没有 CI/CD 配置", severity="info", rule_id="SEC-018")]
    return []


# ══════════════════════════════════════════════════════════════════
# SEC-019: node_modules/vendor 被提交到 Git
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-019", "Dependency", "low",
    "node_modules/vendor 被提交到 Git 仓库",
    "依赖目录被 Git 跟踪会使仓库体积巨大（轻松超过 100MB），clone 极慢，diff 无法阅读。",
    "将 node_modules/, vendor/, .gradle/ 等加入 .gitignore 并从仓库中移除",
    "Git - .gitignore\nhttps://git-scm.com/docs/gitignore"
)
def check_vendor_committed(root: Path):
    issues = []
    if not (root / ".git").exists():
        return issues
    for dirname in ["node_modules", "vendor", ".gradle"]:
        try:
            r = subprocess.run(
                ["git", "-C", str(root), "ls-files", dirname],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                issues.append(make_finding(
                    dirname, 1, f"{dirname}/ 被 Git 跟踪了（{len(r.stdout.splitlines())} 个文件）",
                    severity="low", rule_id="SEC-019",
                ))
        except Exception:
            pass
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-020: 默认管理员密码
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-020", "Security Configuration", "critical",
    "默认管理员密码/凭据未修改",
    "代码中硬编码了默认管理员密码或测试账号密码。攻击者知道这些默认值，"
    "如果上线前没改，等于给攻击者留了后门。",
    "在 .env 中设置 ADMIN_PASSWORD，不要用代码中的默认值",
    "OWASP A07:2021 – Identification and Authentication Failures\nhttps://owasp.org/Top10/A07_2021-Identification-and-Authentication-Failures/"
)
def check_default_admin(root: Path):
    issues = []
    patterns = [r'admin123', r'password123', r'admin\s*=\s*[\'"]admin[\'"]', r'pass\s*=\s*[\'"]pass[\'"]']
    for f in _rglob(root, "*.py"):
        content = _fread(f)
        if not content:
            continue
        # 跳过扫描器自身的规则文件（含有 @register 装饰器的文件不是生产代码）
        if "@register" in content:
            continue
        if "admin" in content.lower() or "password" in content.lower():
            for pat in patterns:
                for m in re.finditer(pat, content, re.I):
                    ln = content[:m.start()].count("\n") + 1
                    issues.append(make_finding(
                        _rel(f, root), ln, m.group()[:60],
                        severity="critical", rule_id="SEC-020",
                    ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-021: CORS 配置过于宽松
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-021", "Security Configuration", "medium",
    "CORS 配置过于宽松（允许 *）",
    "CORS 设置了 '*' 允许所有来源访问。生产环境应该限制到具体的域名。"
    "否则任意网站都可以通过用户浏览器向你的 API 发送请求。",
    "明确列出允许的来源、方法和请求头，不要用 '*'",
    "OWASP A01:2021 – Broken Access Control\nhttps://owasp.org/Top10/A01_2021-Broken-Access-Control/"
)
def check_cors_wildcard(root: Path):
    issues = []
    for f in _rglob(root, "*.py"):
        content = _fread(f)
        if not content:
            continue
        if "allow_origins" in content and '"*"' in content:
            for i, line in enumerate(content.splitlines(), 1):
                if "allow_origins" in line and '"*"' in line:
                    issues.append(make_finding(
                        _rel(f, root), i, line.strip()[:60],
                        severity="medium", rule_id="SEC-021",
                    ))
    return issues


# ══════════════════════════════════════════════════════════════════
# SEC-022: DEBUG 模式未关闭
# ══════════════════════════════════════════════════════════════════

@register(
    "SEC-022", "Security Configuration", "high",
    "DEBUG 模式在生产环境可能未关闭",
    "代码中直接写了 DEBUG=True 而不是从环境变量读取。DEBUG 模式会暴露错误详情、"
    "堆栈追踪甚至源代码路径给最终用户。",
    "确保用环境变量控制 DEBUG 开关: os.getenv('DEBUG', 'false').lower() == 'true'",
    "OWASP A05:2021 – Security Misconfiguration\nhttps://owasp.org/Top10/A05_2021-Security-Misconfiguration/"
)
def check_debug_mode(root: Path):
    issues = []
    for f in _rglob(root, "*.py"):
        if "test" in str(f.parent.name):
            continue
        content = _fread(f)
        if not content:
            continue
        if "DEBUG" in content and ("True" in content or "true" in content):
            for i, line in enumerate(content.splitlines(), 1):
                if "DEBUG" in line and ("True" in line or "true" in line):
                    if "debug=True" in line or "DEBUG=true" in line or "os.getenv" not in line:
                        issues.append(make_finding(
                            _rel(f, root), i, line.strip()[:60],
                            severity="high", rule_id="SEC-022",
                        ))
    return issues
