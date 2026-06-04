# 🛡️ Auditize CLI

**AI 项目确定性安全审查工具 — 告诉你要从哪里看起，而不是丢给你一个列表。**

```
$ auditize scan .

  健康度   ████████░░  B  (72/100)
  
  □ 1. 🔴 修复 src/config.py:42   API Key 硬编码     ~2min
  □ 2. 🟠 修复 .gitignore         缺少 .env 保护     ~1min
  
  3 项要处理 ≈ 6 分钟
```

---

## 安装

```bash
pip install auditize-cli
```

不需要任何第三方依赖，不需要 AI 模型，不需要 API Key。

系统要求: Python 3.8+ (Linux / macOS / WSL2 / Windows)

---

## 快速开始

```bash
# 进入你的项目目录
cd my-awesome-project

# 扫一遍
auditize scan .

# 看看具体要修什么
auditize scan . --plan

# 修完标记一下
auditize fix .

# 再扫一遍，确认干净了
auditize scan .
```

---

## 所有命令

### `auditize scan` — 扫描项目

| 用法 | 说明 |
|---|---|
| `auditize scan .` | 默认模式：健康度条 + 关键问题 + 其余折叠 |
| `auditize scan /path/to/project` | 扫描指定项目 |
| `auditize scan . --plan` | **行动计划**：清单式「先修这 3 项，再修这 2 项」 |
| `auditize scan . --verbose` | 展开全部发现项 |
| `auditize scan . --quick` | 快速模式：只扫 critical / high / medium |
| `auditize scan . --json` | JSON 输出（给 CI 集成） |
| `auditize scan . --no-cache` | 忽略修复记录，重新显示全部 |

输出内容：
- **健康度条 + 等级 (A/B/C/D)** — 一眼知道项目状态
- **严重等级分组** — 必须修 / 建议修 / 可忽略
- **每条含**: 行号、代码片段、修复建议、参考来源

### `auditize fix` — 修复追踪

| 用法 | 说明 |
|---|---|
| `auditize fix .` | 标记当前所有问题为已修复 |
| `auditize fix . --status` | 查看修复进度 |
| `auditize fix . --reset` | 重置修复记录 |

修复记录保存在项目根目录的 `.auditize/status.json` 中，可提交到 Git 让团队共享进度。

### `auditize explain` — 规则详解

```bash
auditize explain SEC-001
```

查看某条规则的完整说明：为什么是问题、怎么修、OWASP 参考链接、验证方法。

### `auditize rules` — 规则列表

```bash
auditize rules list
auditize rules list --category Secret  # 按分类筛选
```

列出所有 22 条扫描规则及其严重等级。

### `auditize version`

查看版本号。

---

## 扫描规则一览

| 编号 | 分类 | 等级 | 说明 |
|---|---|---|---|
| SEC-001 | Secret Leak | 🔴 Critical | API Key / Secret 硬编码在源码中 |
| SEC-002 | Secret Leak | 🟠 High | .env 文件未被 .gitignore 保护 |
| SEC-003 | Git Leak | 🟠 High | Git 历史中曾提交过敏感文件 |
| SEC-004 | Git Leak | 🟡 Medium | .gitignore 缺少关键规则 |
| SEC-005 | SSL Certificate | 🔴 Critical | SSL 私钥文件在项目目录中 |
| SEC-006 | Debug Artifact | 🟡 Medium | 生产代码残留调试输出 |
| SEC-007 | Code Marker | 🔵 Low | TODO/FIXME 累计 |
| SEC-008 | File Permission | 🟡 Medium | 敏感文件权限过于宽松 |
| SEC-009 | Hardcoded Path | 🟡 Medium | 硬编码本地绝对路径 |
| SEC-010 | Database | 🟠 High | 数据库文件可被 Web 下载 |
| SEC-011 | Large File | 🔵 Low | 项目中存在大文件 |
| SEC-012 | Docker | 🟡 Medium | Docker 端口暴露到公网 |
| SEC-013 | Docker | 🔵 Low | 使用了 `latest` 标签 |
| SEC-014 | Dependency | 🟡 Medium | 依赖未固定版本号 |
| SEC-015 | Error Handling | 🟡 Medium | 空的 catch/except 块 |
| SEC-016 | Documentation | 🔵 Low | 缺少 README |
| SEC-017 | Documentation | 🔵 Low | 缺少 LICENSE |
| SEC-018 | CI/CD | ⚪ Info | 缺少 CI/CD 配置 |
| SEC-019 | Dependency | 🔵 Low | node_modules/vendor 被提交 |
| SEC-020 | Security Config | 🔴 Critical | 默认管理员密码 |
| SEC-021 | Security Config | 🟡 Medium | CORS 配置过于宽松 |
| SEC-022 | Security Config | 🟠 High | DEBUG 模式未关闭 |

全部规则文档开源可审计：参见 `cli/rules/` 目录。

---

## 信任机制

Auditize CLI 的信任建立在**透明度**上，而非品牌：

1. **确定性规则** — 纯正则匹配，无 AI 幻觉。每条发现你都可以在对应行号处自行验证
2. **规则开源** — 所有规则以 Markdown 格式放在 `cli/rules/`，写明了检测逻辑和验证方法
3. **参考来源** — 每条规则关联 OWASP Top 10、CVE 或官方文档
4. **宁可漏不可错** — 不确定的问题不报。你得到的每一条都是 100% 可复现的

---

## 谁适合用这个工具

- **独立开发者** — AI 帮你生成了项目，你不想逐行 review 全部代码
- **小团队技术负责人** — 你带 1-2 个人，需要在上线前有个"安全凭证"
- **外包接单者** — 交付给客户时，附带一份安全报告，证明代码经过审查
- **写 OS 的人** — 隔段时间跑一遍，看看项目有没有引入不该有的东西 😉

---

## 和市面上其他工具的区别

| | Auditize | Snyk | Semgrep | linter |
|---|---|---|---|---|
| 安装 | `pip install` | 注册账号 | `pip install` | 语言特定 |
| 规则是否开源 | ✅ 全部开源 | ❌ 部分付费 | ✅ 开源 | ✅ |
| 是否有 AI 幻觉 | ❌ 完全无 | ❌ | ❌ | ❌ |
| 是否有行动计划 | ✅ `--plan` | ❌ | ❌ | ❌ |
| 是否有修复追踪 | ✅ `auditize fix` | ❌ | ❌ | ❌ |
| 是否面向 AI 生成代码 | ✅ 是 | ❌ 传统项目 | ❌ 通用 | ❌ 语法级 |

---

## 项目结构

```
cli/
├── __init__.py      # 版本号
├── __main__.py      # python -m cli 入口
├── main.py          # 命令行入口
├── scanner.py       # 扫描引擎 + 项目检测
├── rules.py         # 22 条扫描规则
├── output.py        # 输出格式 (默认/plan/json/explain)
├── rules/           # 规则文档（开源可审计）
│   ├── README.md
│   ├── SEC-001.md
│   └── ...
└── README.md        # 本文件
```

## License

MIT

---

## 🌐 网页平台

本仓库同时包含 **Truffle AI 网页平台** —— 全栈 AI 代码生成 + 安全扫描 + 团队协作应用。

| 组件 | 目录 | 技术栈 |
|------|------|--------|
| 前端 | [`website/frontend/`](/website/frontend/) | React + TypeScript + Vite + Tailwind |
| 后端 | [`website/backend/`](/website/backend/) | FastAPI + Python + SQLite |
| 部署 | [`website/deploy/`](/website/deploy/) | Docker Compose + Nginx |

👉 [平台文档](/website/docs/README.md)
