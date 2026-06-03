"""
TruffleKit 输出格式
==================
三种输出模式:
  1. 默认模式 — 健康度条 + 关键行动项（最常用）
  2. 行动计划模式 (--plan) — 清单式修复指引
  3. JSON 模式 (--json) — 给 CI 集成用
  4. Explain 模式 (explain 子命令) — 规则详解
"""

import shutil
from pathlib import Path

from . import __version__
from .scanner import RULES, RULE_MAP

try:
    TERM_WIDTH = shutil.get_terminal_size().columns
except Exception:
    TERM_WIDTH = 80


def _bar(value: int, total: int = 100, width: int = 20) -> str:
    """渲染进度条"""
    filled = int(value / max(total, 1) * width)
    filled = min(filled, width)
    bar = "█" * filled + "░" * (width - filled)
    return bar


def _color(severity: str) -> str:
    """返回 emoji 标识"""
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(severity, "⚪")


def _est_time(finding) -> int:
    """估计修复时间（分钟）"""
    return {"critical": 5, "high": 3, "medium": 2, "low": 1, "info": 0}.get(finding.get("severity", "low"), 1)


def _grade_color(grade: str) -> str:
    return {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}.get(grade, "⚪")


# ── Banner ──────────────────────────────────────────────────────

def print_banner():
    """打印品牌标识——粉猪猪"""
    print(f"   🐷    ◕ ‿ ◕   TruffleKit v{__version__}")
    print(f"       （   ）   确定性审查 · 22 条规则")
    print(f"         ω      Zero AI · Open Source")
    print()


# ── 默认模式 ────────────────────────────────────────────────────

def _print_section_header(title: str, char: str = "─"):
    """打印分段标题"""
    print(f"  ─── {title} {char * max(0, TERM_WIDTH - len(title) - 10)}{char * 3}")


def print_default(result: dict):
    """默认输出：健康度 + 关键项 + 其余折叠"""
    print_banner()

    # 项目概况
    langs = ", ".join(result["languages"]) if result["languages"] else "未知"
    print(f"  项目: {result['project_name']}  ({langs})")
    print(f"  文件: {result['code_files']} 个代码文件  |  规则: {result['rules_loaded']} 条")
    print(f"  用时: {result['elapsed']}s")
    print()

    # 健康度
    grade_colored = f"{_grade_color(result['grade'])} {result['grade']}"
    print(f"  健康度   {_bar(result['health_score'])}  {grade_colored}  ({result['health_score']}/100)")
    print(f"  说明:    {result['grade_label']}")
    print()

    # 发现概览
    sc = result["severity_counts"]
    parts = []
    for sev in ["critical", "high", "medium", "low", "info"]:
        cnt = sc.get(sev, 0)
        if cnt:
            parts.append(f"{_color(sev)} {sev.capitalize()} {cnt}")
    if parts:
        print(f"  发现:    {'  '.join(parts)}")
        print()

    # 必须处理区
    must = result.get("must_fix", [])
    should = result.get("should_fix", [])
    ignore = result.get("can_ignore", [])

    if must:
        _print_section_header("必须处理")
        print()
        for f in must:
            sev = f["severity"]
            rid = f.get("rule_id", "???")
            print(f"  {_color(sev)}  {sev.upper():6s}  {rid}  {f.get('rule_title', '?')}")
            print(f"        {f['file']}:{f.get('line', '?')}  →  {f.get('snippet', '')[:80]}")
            print(f"        修复: {f.get('recommendation', '')[:80]}")
            print()
        _print_section_header("")
        print()

    if should:
        if not must:
            _print_section_header("建议处理")
            print()
        for f in should[:6]:  # 最多显示 6 条
            rid = f.get("rule_id", "???")
            print(f"  {_color('medium')}  {rid}  {f.get('rule_title', '?')}")
            print(f"        {f['file']}:{f.get('line', '?')}  →  {f.get('snippet', '')[:60]}")
        if len(should) > 6:
            print(f"        ... 及另外 {len(should) - 6} 项")
        if not must:
            print()

    # 折叠信息
    total = result["total_findings"]
    shown = len(must) + min(len(should), 6)
    hidden = total - shown
    if hidden > 0:
        print(f"  其余 {hidden} 项已自动折叠，使用 --verbose 查看全部  |  ", end="")
    print(f"需要行动计划？  truffle scan . --plan")
    print()

    # 底部统计
    _print_section_header("")
    total_time = sum(_est_time(f) for f in must + should)
    if total_time > 0:
        print(f"  {len(must) + len(should)} 项要处理  ≈ 约 {max(total_time, 1)} 分钟")
    if not must and not should:
        print(f"  ✅ 未发现需要处理的问题，项目整体状况良好")
    print()


# ── Verbose 模式 ────────────────────────────────────────────────

def print_verbose(result: dict):
    """详细模式：显示全部 findings"""
    print_banner()
    langs = ", ".join(result["languages"]) if result["languages"] else "未知"
    print(f"  项目: {result['project_name']}  ({langs})  |  {result['code_files']} 个文件")
    print(f"  健康度: {result['grade']} ({result['health_score']}/100)  |  {result['grade_label']}")
    print()

    findings = result["findings"]
    if not findings:
        print("  ✅ 未发现问题")
        return

    for i, f in enumerate(findings, 1):
        sev = f["severity"]
        rid = f.get("rule_id", "???")
        print(f"  {_color(sev)}  [{i:3d}] {sev.upper():6s}  {rid}  {f.get('rule_title', '?')}")
        print(f"         文件: {f['file']}:{f.get('line', '?')}")
        print(f"         详情: {f.get('snippet', '')[:100]}")
        rec = f.get("recommendation", "")
        if rec:
            print(f"         修复: {rec[:100]}")
        print()

    sc = result["severity_counts"]
    parts = [f"  共 {result['total_findings']} 项:"]
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sc.get(sev, 0):
            parts.append(f"{_color(sev)} {sev.capitalize()} {sc[sev]}")
    print("  ".join(parts))
    print()


# ── 行动计划模式 ────────────────────────────────────────────────

def print_plan(result: dict):
    """行动计划模式：清单式输出"""
    print_banner()
    print(f"  📋 行动计划")
    print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
    print(f"  项目: {result['project_name']}")
    print()

    must = result.get("must_fix", [])
    should = result.get("should_fix", [])
    ignore = result.get("can_ignore", [])

    must_time = sum(_est_time(f) for f in must)
    should_time = sum(_est_time(f) for f in should)
    total_time = max(must_time + should_time, 1)

    print(f"  你需要处理的有 {len(must) + len(should)} 项 (预计约 {total_time} 分钟)")
    if ignore:
        print(f"  另外 {len(ignore)} 项可忽略，不影响上线")
    print()

    # 第一步：必须修
    if must:
        print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
        print(f"  第一步：必须修 ({len(must)} 项 · 约 {max(must_time, 1)} 分钟)")
        print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
        print()
        for i, f in enumerate(must, 1):
            rid = f.get("rule_id", "???")
            sev = f["severity"]
            print(f"  □  {i:2d}. {_color(sev)} {rid}  {f.get('rule_title', '?')}")
            print(f"       文件: {f['file']}:{f.get('line', '?')}")
            print(f"       代码: {f.get('snippet', '')[:80]}")
            rec = f.get("recommendation", "")
            if rec:
                print(f"       修复: {rec[:100]}")
            ref = f.get("reference", "")
            if ref:
                # 只显示第一行引用
                ref_line = ref.split("\n")[0].strip()
                print(f"       参考: {ref_line}")
            print(f"       ✓ 修好后下次扫描自动消失")
            print()

    # 第二步：建议修
    if should:
        if not must:
            print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
        print(f"  第二步：建议修 ({len(should)} 项 · 约 {max(should_time, 1)} 分钟)")
        print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
        print()
        for i, f in enumerate(should, 1):
            rid = f.get("rule_id", "???")
            print(f"  □  {i:2d}. {_color('medium')} {rid}  {f.get('rule_title', '?')}")
            print(f"       文件: {f['file']}:{f.get('line', '?')}  |  {f.get('snippet', '')[:60]}")
            rec = f.get("recommendation", "")
            if rec:
                print(f"       修复: {rec[:80]}")
            print()

    # 第三步：可忽略
    if ignore:
        print()
        print(f"  ─── 可忽略 ({len(ignore)} 项 · 全为 low/info) ───")
        for f in ignore[:5]:
            rid = f.get("rule_id", "???")
            print(f"  · {rid}  {f.get('rule_title', '?')}  —  {f['file']}:{f.get('line', '?')}")
        if len(ignore) > 5:
            print(f"  · ... 及另外 {len(ignore) - 5} 项（使用 --verbose 查看全部）")
        print()

    # 总结
    print(f"  {'═' * max(TERM_WIDTH - 4, 30)}")
    if not must and not should:
        print(f"   ✅ 项目整体状况良好，未发现需要处理的问题")
    elif not must:
        print(f"   ✅ 无高风险问题，{len(should)} 项建议择机修复")
    else:
        print(f"   🔴 请先修复 {len(must)} 项高风险问题再上线")
    print(f"   修复后重扫:  truffle scan .")
    if must or should:
        print(f"   标记已修复:  truffle fix <项目路径>")
    print()


# ── JSON 模式 ───────────────────────────────────────────────────

def print_json(result: dict):
    """JSON 输出（给 CI 集成用）"""
    import json
    # 简化输出，去掉内部字段
    output = {
        "project": result["project"],
        "scanned_at": result["scanned_at"],
        "elapsed": result["elapsed"],
        "languages": result["languages"],
        "code_files": result["code_files"],
        "total_findings": result["total_findings"],
        "severity_counts": result["severity_counts"],
        "health_score": result["health_score"],
        "grade": result["grade"],
        "grade_label": result["grade_label"],
        "findings": [
            {
                "rule_id": f.get("rule_id"),
                "rule_title": f.get("rule_title"),
                "severity": f["severity"],
                "file": f["file"],
                "line": f.get("line"),
                "snippet": f.get("snippet", ""),
                "recommendation": f.get("recommendation", ""),
                "reference": f.get("reference", "").split("\n")[0] if f.get("reference") else "",
            }
            for f in result["findings"]
        ],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


# ── Explain 模式 ────────────────────────────────────────────────

def print_explain(rule_id: str):
    """显示某条规则的详细解释"""
    rule = RULE_MAP.get(rule_id.upper())
    if not rule:
        print_banner()
        print(f"\n  ❌ 未找到规则: {rule_id}")
        print(f"  可用规则: truffle rules list\n")
        return
    print_banner()

    sev = rule["severity"]
    sev_icon = _color(sev)
    print()
    print(f"  ── {rule_id}  {rule['title']}  ──")
    print(f"  分类:    {rule['category']}")
    print(f"  等级:    {sev_icon} {sev.upper()}")
    print()
    print(f"  为什么这是一个问题:")
    print(f"    {rule['description']}")
    print()
    print(f"  修复建议:")
    print(f"    {rule['recommendation']}")
    print()

    # 参考链接
    ref = rule.get("reference", "")
    if ref:
        print(f"  参考来源:")
        for line in ref.split("\n"):
            line = line.strip()
            if line:
                print(f"    · {line}")
        print()

    # 检测逻辑说明（如果是 Python 规则，展示正则的小总结）
    print(f"  检测方式: 确定性规则匹配（无 AI 幻觉）")
    print(f"  效果:     用户可在对应行号处自行验证结果")
    print()


# ── Rules list 模式 ─────────────────────────────────────────────

def print_rules_list(category: str = None):
    """列出所有规则"""
    print_banner()
    print(f"  TruffleKit 规则库 ({len(RULES)} 条)")
    print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
    print()

    # 按分类分组
    from collections import defaultdict
    by_cat = defaultdict(list)
    for r in RULES:
        by_cat[r["category"]].append(r)

    seen = set()
    for cat in sorted(by_cat.keys()):
        if category and cat.lower() != category.lower():
            continue
        print(f"  [{cat}]")
        for r in by_cat[cat]:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            sev_icon = _color(r["severity"])
            desc = r["description"][:60] + "..." if len(r["description"]) > 60 else r["description"]
            print(f"    {sev_icon}  {r['id']:8s}  {r['severity']:8s}  {r['title'][:40]:40s}")
        print()

    print(f"  查看规则详情:  truffle explain SEC-001")
    print(f"  参考来源均来自 OWASP / CVE / 官方文档")
    print()


# ── Fix 模式 ────────────────────────────────────────────────────

def print_fix_done(project_root: Path, count: int):
    """标记已修复的反馈"""
    pname = project_root.name if isinstance(project_root, Path) else str(project_root)
    if count > 0:
        print(f"\n  ✅ 已标记 {count} 项为已修复")
        print(f"  下次扫描将不再显示这些项:  truffle scan {pname}")
    else:
        print(f"\n  未找到匹配项")
    print()


def print_fix_reset(project_root: Path):
    """重置修复记录的反馈"""
    print(f"\n  🔄 已重置修复记录")
    print(f"  下次扫描将重新显示所有项")
    print()


def print_fix_status(project_root: Path, fixed_count: int, total_findings: int):
    """查看当前修复进度"""
    print()
    print(f"  📊 修复进度 — {project_root.name}")
    print(f"  {'─' * max(TERM_WIDTH - 4, 30)}")
    print(f"  已修复: {fixed_count} 项")
    print(f"  待修复: {total_findings} 项")
    if total_findings > 0:
        pct = int(fixed_count / max(fixed_count + total_findings, 1) * 100)
        print(f"  进度:   {_bar(pct)}  {pct}%")
    else:
        print(f"  进度:   {_bar(100)}  100% ✅")
    print()
