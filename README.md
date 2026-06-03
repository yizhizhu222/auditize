# 🍄 TruffleKit CLI

**AI 项目确定性安全审查工具 — 告诉你要从哪里看起，而不是丢给你一个列表。**

```bash
pip install trufflekit
truffle scan . --plan
```

---

## 快速开始

```bash
# 安装
pip install trufflekit

# 扫描你的项目
cd your-ai-project
truffle scan .

# 查看行动计划
truffle scan . --plan

# 查看规则详解
truffle explain SEC-001
```

## 文档

- [CLI 使用说明](cli/README.md) — 所有命令和选项
- [规则库](cli/rules/README.md) — 22 条规则的开源文档
- [发布指南](cli/PUBLISH.md) — 如何发布到 PyPI

## 声明

确定性规则匹配，无 AI 幻觉，每条结果都可在对应行号处自行验证。
