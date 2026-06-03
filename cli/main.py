"""
TruffleKit CLI 入口
==================
truffle scan .              # 默认模式 — 健康度 + 关键项
truffle scan . --plan       # 行动计划 — 清单式
truffle scan . --json       # JSON — CI 集成
truffle scan . --verbose    # 全部展开
truffle scan . --quick      # 只扫 critical/high/medium
truffle fix .               # 标记已修复
truffle fix . --reset       # 重置修复记录
truffle fix . --status      # 查看修复进度
truffle explain SEC-001     # 查看规则详解
truffle rules list          # 列出所有规则
"""

import sys
import argparse
from pathlib import Path

from . import __version__
from .scanner import scan_project, load_status, mark_fixed, mark_all_fixed, reset_status, finding_key
from .output import (
    print_default, print_verbose, print_plan, print_json,
    print_explain, print_rules_list,
    print_fix_done, print_fix_reset, print_fix_status,
    print_banner,
)


def main():
    parser = argparse.ArgumentParser(
        prog="truffle",
        description="🍄  TruffleKit AI Code Audit  —  确定性安全审查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  truffle scan .                         # 扫描当前项目
  truffle scan /path/to/project --plan   # 行动计划模式
  truffle scan . --json                  # JSON 输出（CI 集成）
  truffle explain SEC-001                # 查看规则详解
  truffle rules list                     # 列出所有规则
  truffle fix .                          # 标记当前项目问题已修复

文档:  https://trufflekit.com
规则:  https://github.com/trufflekit/truffle/tree/main/cli/rules
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── scan ──────────────────────────────────────────────────
    scan_parser = subparsers.add_parser("scan", help="扫描项目安全问题和代码质量")
    scan_parser.add_argument("path", nargs="?", default=".", help="项目路径（默认当前目录）")
    scan_parser.add_argument("--plan", action="store_true", help="行动计划模式：清单式输出")
    scan_parser.add_argument("--json", action="store_true", help="JSON 格式输出（CI 集成）")
    scan_parser.add_argument("--verbose", action="store_true", help="显示全部发现项，不折叠")
    scan_parser.add_argument("--quick", action="store_true", help="快速模式：只扫 critical/high/medium")
    scan_parser.add_argument("--no-cache", action="store_true", help="忽略已修复记录，重新显示全部")

    # ── fix ───────────────────────────────────────────────────
    fix_parser = subparsers.add_parser("fix", help="标记已修复/查看修复进度")
    fix_parser.add_argument("path", nargs="?", default=".", help="项目路径（默认当前目录）")
    fix_parser.add_argument("--rule", "-r", help="只标记指定规则编号的项，如 SEC-001")
    fix_parser.add_argument("--file", "-f", help="只标记指定文件中的项，如 deploy/ca.key")
    fix_parser.add_argument("--reset", action="store_true", help="重置修复记录")
    fix_parser.add_argument("--status", action="store_true", help="查看修复进度")

    # ── explain ───────────────────────────────────────────────
    explain_parser = subparsers.add_parser("explain", help="查看规则详解")
    explain_parser.add_argument("rule_id", help="规则编号，如 SEC-001")

    # ── rules ─────────────────────────────────────────────────
    rules_parser = subparsers.add_parser("rules", help="查看规则列表")
    rules_parser.add_argument("list", nargs="?", default="list", help="列出所有规则")
    rules_parser.add_argument("--category", "-c", help="按分类筛选")

    # ── version ───────────────────────────────────────────────
    version_parser = subparsers.add_parser("version", help="查看版本")
    version_parser.add_argument("--version", action="store_true", help=argparse.SUPPRESS)

    # ── 无参数时 ──────────────────────────────────────────────
    if len(sys.argv) == 1 or sys.argv[1] in ("--version", "-v"):
        if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-v"):
            print(f"truffle version {__version__}")
        else:
            parser.print_help()
        return

    args = parser.parse_args()

    # ── 分发 ──────────────────────────────────────────────────

    if args.command == "scan":
        _handle_scan(args)
    elif args.command == "fix":
        _handle_fix(args)
    elif args.command == "explain":
        _handle_explain(args)
    elif args.command == "rules":
        _handle_rules(args)
    elif args.command == "version":
        print(f"truffle version {__version__}")
    else:
        parser.print_help()


# ── scan ────────────────────────────────────────────────────────

def _handle_scan(args):
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"❌ 路径不存在: {path}")
        sys.exit(1)

    result = scan_project(
        path,
        quick=args.quick,
        hide_fixed=not args.no_cache,
    )

    if args.json:
        print_json(result)
    elif args.plan:
        print_plan(result)
    elif args.verbose:
        print_verbose(result)
    else:
        print_default(result)


# ── fix ─────────────────────────────────────────────────────────

def _handle_fix(args):
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"❌ 路径不存在: {path}")
        sys.exit(1)

    from .scanner import get_status_path, load_status, scan_project
    status_path = get_status_path(path)

    if args.reset:
        reset_status(path)
        print_fix_reset(path)
    elif args.status:
        status = load_status(path)
        fixed_count = len(status.get("fixed", []))
        result = scan_project(path, hide_fixed=False)
        print_fix_status(path, fixed_count, result["total_findings"])
    elif args.rule or args.file:
        # 按规则或文件筛选后标记
        result = scan_project(path, hide_fixed=False)
        findings = result["findings"]
        matched = []
        for f in findings:
            if args.rule and f.get("rule_id", "").upper() != args.rule.upper():
                continue
            if args.file and args.file not in f.get("file", ""):
                continue
            matched.append(f)

        if not matched:
            filter_desc = f"规则 {args.rule}" if args.rule else f"文件 {args.file}"
            print(f"\n  ℹ️ 未找到匹配 {filter_desc} 的未修复项")
            return

        keys = [finding_key(f) for f in matched]
        mark_all_fixed(path, keys)
        filter_desc = f"规则 {args.rule}" if args.rule else f"文件 {args.file}"
        print(f"\n  ✅ 已标记 {len(keys)} 项 ({filter_desc}) 为已修复")
        print(f"  下次扫描将不再显示这些项")
    else:
        # 标记当前所有未修复项为已修复
        result = scan_project(path, hide_fixed=False)
        findings = result["findings"]
        if not findings:
            print(f"\n  ✅ 未发现问题，无需标记")
            return
        keys = [finding_key(f) for f in findings]
        mark_all_fixed(path, keys)
        print_fix_done(path, len(keys))


# ── explain ─────────────────────────────────────────────────────

def _handle_explain(args):
    print_explain(args.rule_id)


# ── rules list ──────────────────────────────────────────────────

def _handle_rules(args):
    category = getattr(args, "category", None)
    print_rules_list(category=category)


if __name__ == "__main__":
    main()
