"""
TruffleKit 扫描引擎
==================
运行所有规则并汇总结果。支持进度追踪（标记已修复后不再显示）。
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from .rules import RULES, RULE_MAP

TRUFFLE_DIR = ".truffle"
STATUS_FILE = "status.json"


def get_status_path(project_root: Path) -> Path:
    """获取项目的 .truffle/status.json 路径"""
    p = project_root / TRUFFLE_DIR
    p.mkdir(exist_ok=True)
    return p / STATUS_FILE


def load_status(project_root: Path) -> dict:
    """加载已修复记录"""
    sp = get_status_path(project_root)
    if sp.exists():
        try:
            return json.loads(sp.read_text())
        except (json.JSONDecodeError, Exception):
            return {"fixed": []}
    return {"fixed": []}


def save_status(project_root: Path, status: dict):
    """保存已修复记录"""
    sp = get_status_path(project_root)
    sp.write_text(json.dumps(status, indent=2, ensure_ascii=False))


def mark_fixed(project_root: Path, finding_key: str):
    """标记一条发现为已修复"""
    status = load_status(project_root)
    if finding_key not in status["fixed"]:
        status["fixed"].append(finding_key)
    save_status(project_root, status)


def mark_all_fixed(project_root: Path, finding_keys: list[str]):
    """批量标记为已修复"""
    status = load_status(project_root)
    for key in finding_keys:
        if key not in status["fixed"]:
            status["fixed"].append(key)
    save_status(project_root, status)


def reset_status(project_root: Path):
    """重置所有修复记录"""
    sp = get_status_path(project_root)
    if sp.exists():
        sp.unlink()
    return {"fixed": []}


def finding_key(finding: dict) -> str:
    """生成唯一的发现 key 用于追踪"""
    return f"{finding['rule_id']}:{finding['file']}:{finding['line']}"


# ── 项目检测 ────────────────────────────────────────────────────

def detect_languages(root: Path) -> set:
    """检测项目使用的编程语言"""
    languages = set()
    for f in root.iterdir():
        name = f.name
        if f.is_file():
            if name == "package.json" or name == "package-lock.json":
                languages.add("JavaScript")
            if name == "requirements.txt" or name == "Pipfile" or name == "pyproject.toml":
                languages.add("Python")
            if name == "go.mod" or name == "go.sum":
                languages.add("Go")
            if name == "Cargo.toml":
                languages.add("Rust")
            if name == "pom.xml" or name == "build.gradle":
                languages.add("Java")
            if name == "CMakeLists.txt" or name.endswith((".csproj", ".sln")):
                languages.add("C#")
            if name == "Gemfile":
                languages.add("Ruby")
            if name == "composer.json":
                languages.add("PHP")
    # 按文件扩展名补充检测
    ext_to_lang = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React", ".tsx": "React", ".go": "Go",
        ".rs": "Rust", ".java": "Java", ".c": "C",
        ".cpp": "C++", ".h": "C/C++", ".cs": "C#",
        ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
        ".kt": "Kotlin", ".scala": "Scala", ".r": "R",
        ".dart": "Dart", ".lua": "Lua",
    }
    ext_count = defaultdict(int)
    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ext_to_lang:
                ext_count[ext_to_lang[ext]] += 1
    for lang, count in ext_count.items():
        if count >= 3:
            languages.add(lang)
    return languages or {"未知"}


def count_code_files(root: Path) -> int:
    """统计项目中代码文件数量"""
    code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
                 ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
                 ".kt", ".scala", ".sh", ".bash", ".zsh", ".r", ".dart",
                 ".lua", ".pl", ".pm", ".yaml", ".yml", ".json", ".toml",
                 ".md", ".sql", ".css", ".scss", ".less", ".html", ".vue",
                 ".svelte", ".astro"}
    count = 0
    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in code_exts:
                count += 1
    return count


# ── 误报过滤器 ──────────────────────────────────────────────────

SCANNER_FP_PREFIXES = {
    "cli/rules",       # 规则文档中的示例代码
    "cli/rules/",      # (带斜杠)
}


def _is_scanner_false_positive(finding: dict, project_root: Path) -> bool:
    """
    判断一条发现是否来自扫描器自身的源码或文档。
    这些文件中的"问题"是刻意包含的示例或规则定义，不是真正的安全风险。
    """
    filepath = finding.get("file", "")
    if not filepath or filepath.startswith("(project-wide)") or filepath.startswith("(git-history)"):
        return False

    # 规则文档目录下的 markdown 文件（包含刻意示例代码）
    if filepath.startswith("cli/rules/") or "/cli/rules/" in filepath:
        return True

    # 完全匹配的旧式 standalone 文件
    if filepath in ("truffle-audit.py", "truffle-scan.py", "scan.py"):
        return True

    # 检查源文件是否包含 @register（说明是扫描器自身的规则定义文件，不是生产代码）
    try:
        full_path = project_root / filepath
        if full_path.is_file():
            content = full_path.read_text(errors="ignore")
            if "@register" in content:
                return True
    except Exception:
        pass

    return False


# ── 扫描主逻辑 ──────────────────────────────────────────────────

def scan_project(project_root: Path, quick: bool = False, hide_fixed: bool = True) -> dict:
    """
    执行扫描，返回结构化结果。

    返回:
        {
            "project": str,
            "languages": [str],
            "code_files": int,
            "scanned_at": str,
            "elapsed": float,
            "findings": [finding],
            "total_findings": int,
            "severity_counts": {severity: count},
            "score": int,       # 0-100, 越低越安全
            "grade": str,       # A/B/C/D
            "grade_label": str,
            "critical_count": int,
            "high_count": int,
            "medium_count": int,
            "low_count": int,
            "info_count": int,
            "must_fix": [finding],
            "should_fix": [finding],
            "can_ignore": [finding],
        }
    """
    start = datetime.now()

    languages = detect_languages(project_root)
    code_files = count_code_files(project_root)

    fixed_status = load_status(project_root) if hide_fixed else {"fixed": []}
    fixed_set = set(fixed_status.get("fixed", []))

    all_findings = []
    severity_counts = defaultdict(int)
    grade_weights = defaultdict(int)  # for scoring

    for rule_def in RULES:
        if quick and rule_def["severity"] in ("low", "info"):
            continue
        try:
            findings = rule_def["check"](project_root)
        except Exception:
            continue

        for f in findings:
            sev = f.get("severity", rule_def["severity"])
            f["severity"] = sev
            f["rule_id"] = f.get("rule_id", rule_def["id"])
            f["rule_title"] = rule_def["title"]
            f["category"] = rule_def["category"]
            f["recommendation"] = rule_def["recommendation"]
            f["reference"] = rule_def["reference"]

            # 检查是否已被标记已修复
            key = finding_key(f)
            f["_key"] = key
            if key in fixed_set:
                f["_fixed"] = True
                continue

            f["_fixed"] = False

            # 过滤扫描器自身的误报：规则定义文件和文档示例代码
            if _is_scanner_false_positive(f, project_root):
                continue
            f["_fixed"] = False
            all_findings.append(f)
            severity_counts[sev] += 1
            grade_weights[sev] += 1

    elapsed = (datetime.now() - start).total_seconds()

    # 分级
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda x: (sev_order.get(x["severity"], 99), x["file"], x["line"]))

    # 评分 (0 = 最安全, 100 = 最危险)
    score_weights = {"critical": 30, "high": 15, "medium": 5, "low": 2, "info": 0}
    score = min(sum(score_weights.get(f["severity"], 0) for f in all_findings), 100)

    # 等级
    if score == 0:
        grade, grade_label = "A", "安全 — 未发现问题"
    elif score <= 20:
        grade, grade_label = "A", "安全 — 仅少量低风险问题"
    elif score <= 40:
        grade, grade_label = "B", "良好 — 建议上线前审查"
    elif score <= 60:
        grade, grade_label = "C", "需审查 — 存在中高风险问题"
    else:
        grade, grade_label = "D", "危险 — 存在严重安全风险，请修复后再上线"

    # 分类：must_fix / should_fix / can_ignore
    must_fix = [f for f in all_findings if f["severity"] in ("critical", "high")]
    should_fix = [f for f in all_findings if f["severity"] == "medium"]
    can_ignore = [f for f in all_findings if f["severity"] in ("low", "info")]

    return {
        "project": str(project_root.resolve()),
        "project_name": project_root.name,
        "languages": sorted(languages),
        "code_files": code_files,
        "scanned_at": start.isoformat(),
        "elapsed": round(elapsed, 2),
        "rules_loaded": len(RULES),
        "findings": all_findings,
        "total_findings": len(all_findings),
        "severity_counts": dict(severity_counts),
        "score": score,
        "health_score": 100 - score,
        "grade": grade,
        "grade_label": grade_label,
        "must_fix": must_fix,
        "should_fix": should_fix,
        "can_ignore": can_ignore,
        "must_fix_count": len(must_fix),
        "should_fix_count": len(should_fix),
        "can_ignore_count": len(can_ignore),
    }
