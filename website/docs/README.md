# Truffle AI Platform

> **面向小团队的"需求→审核→开发→资产"协作平台**
>
> 非技术人提需求，技术人审核，AI 生成代码，系统防重复开发。

🌐 [trufflekit.com](https://trufflekit.com)

---

## 📋 目录

- [产品定位](#-产品定位)
- [快速启动](#-快速启动)
- [项目架构](#-项目架构)
- [前端指南](#-前端指南)
- [后端 API 参考](#-后端-api-参考)
- [数据库](#-数据库)
- [安全扫描引擎](#-安全扫描引擎)
- [专家审核流程](#-专家审核流程)
- [部署](#-部署)
- [技术栈](#-技术栈)
- [常见问题](#-常见问题)

---

## 🎯 产品定位

### 目标用户

| 用户类型 | 痛点 | 使用场景 |
|---------|------|---------|
| **1 技术人 + N 非技术人的小团队** | 非技术人有需求，技术人做不完，重复造轮子 | 非技术人提需求 → 技术人审核 → AI 生成 → 资产防重复 |
| **Indie Hacker / 独立开发者** | 多个产品想法需要快速验证 | 描述需求 → AI 生成代码 → 自动安全扫描 → 导出部署 |
| **企业内部 IT 部门** | 业务方天天提需求，IT 做不完 | 放权给业务方提需求，AI 辅助生成，安全由平台兜底 |

### 核心流程

```
非技术成员 A 提交需求："做一个订单管理后台"
非技术成员 B 提交需求："做一个订单看板"
                    ↓
系统自动检测：B 的需求与 A 的 75% 相似
           → 提示"已有类似需求，是否查看？"
                    ↓
技术人 C（reviewer）看到待审核列表：
  ├── A 的"订单管理后台" → 批准 → AI 生成代码 → 资产入库
  ├── B 的"订单看板"    → 标记重复，关联到 A 的需求
  └── (已完成的 5 个需求) → 全员可见，防止再次提出
```

### 差异化

| 对比对象 | 它们做 | 我们做 |
|---------|-------|-------|
| ChatGPT / Claude | 生成代码，你自己验证 | 生成代码 + **自动安全扫描** + 人类可读报告 |
| Bolt.new / Lovable | 生成代码 + 部署 | 生成代码 + **安全分析** + **防重复** |
| 低代码平台 | 拖拽组件，限制能做的东西 | 不限需求，自然语言描述 |
| Snyk / 奇安信 | 面向开发者的代码审计 | 面向 **非技术人员** 的中文/英文安全报告 |

---

## 🚀 快速启动

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问 http://localhost:8001/docs 查看交互式 API 文档。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173。

### 3. 一键启动（开发环境）

```bash
./start.sh
```

自动构建前端 → 启动后端 (:8001) + 管理后台 (:8002) + Cloudflare Tunnel。

### 4. 默认管理员账号

| 用户名 | 密码 | 角色 |
|-------|------|------|
| `admin` | `admin123` | admin |

### 5. 使用步骤

| 步骤 | 操作 |
|------|------|
| 1 | 访问 `http://localhost:5173` → 看到 Landing Page → 点击 **Get Started** |
| 2 | 用 `admin / admin123` 登录 |
| 3 | 跟着 **GuidedTour** 走完 5 步导览（或直接跳过） |
| 4 | 在 **AI Tools** 页面描述你的产品想法，点击 **Generate**（无需 API Key） |
| 5 | 查看安全报告和生成的代码 |
| 6 | 安全 → 保存到 **My Assets** 防止重复开发 |
| 7 | 不放心 → 去 **Expert Review** 提交人工审核（支持 Stripe 付费） |
| 8 | 管理员在 **http://localhost:8002** 审核代码 / 管理用户 |

---

## 🏗️ 项目架构

```
Truffle/
├── cli/                                # Auditize CLI 安全扫描工具
│   └── ...
│
├── website/                            # 网页平台（本目录）
│   ├── logs/                           # 统一日志目录
│   │
│   ├── frontend/                       # 前端 (Vite + React + TypeScript + Tailwind)
│   │   └── src/
│   │       ├── components/
│   │       │   ├── LandingPage.tsx      # 产品首页（/）
│   │       │   ├── Login.tsx            # 登录/注册（/login）
│   │       │   ├── Dashboard.tsx        # 主工作台骨架
│   │       │   ├── Sidebar.tsx          # 导航侧栏
│   │       │   ├── TeamPage.tsx         # 团队需求看板
│   │       │   ├── AssetLibrary.tsx     # 代码资产库（含团队筛选）
│   │       │   ├── MainPage.tsx         # AI 代码生成
│   │       │   ├── SafetyReport.tsx     # 安全报告展示
│   │       │   ├── ReviewPage.tsx       # 专家审核（含 Stripe 支付）
│   │       │   ├── AdminPage.tsx        # 管理员面板（审核 + 用户管理）
│   │       │   ├── SettingsPage.tsx     # 设置（API Key + 主题）
│   │       │   └── ErrorBoundary.tsx    # 错误边界
│   │       └── context/
│   │           ├── LanguageContext.tsx   # 中英文切换
│   │           ├── SettingsContext.tsx   # API Key + 模型列表
│   │           ├── ThemeContext.tsx      # 主题/字体管理
│   │           └── ToastContext.tsx      # Toast 通知
│   │
│   ├── backend/                        # 后端 (FastAPI + Python)
│   │   └── app/
│   │       ├── main.py                 # 入口 + 路由注册
│   │       ├── admin_app.py            # 管理后台 (:8002，仅本地)
│   │       ├── db.py                   # 统一数据库
│   │       ├── auth/auth.py            # 认证 (JWT + TOTP)
│   │       ├── scanner/                # 安全扫描引擎
│   │       │   ├── static_analyzer.py  # Python/JS/Go/C++ 静态分析
│   │       │   └── reporter.py         # 人类可读报告生成
│   │       └── api/
│   │           ├── generate.py         # 需求→代码生成
│   │           ├── scan.py             # 代码安全扫描
│   │           ├── review.py           # 专家审核（含支付状态）
│   │           ├── payment.py          # Stripe Checkout 支付
│   │           ├── assets.py           # 代码资产库 + 重复检测
│   │           ├── chat.py             # AI 聊天代理
│   │           ├── chat_history.py     # 聊天会话历史
│   │           ├── compile.py          # 代码沙箱
│   │           ├── settings.py         # 用户设置
│   │           ├── admin.py            # 管理员（用户管理）
│   │           └── routes.py           # 健康检查 + 版本
│   │
│   ├── deploy/                         # 部署配置
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.tunnel
│   │   ├── nginx.conf
│   │   ├── setup.sh
│   │   └── tunnel-config.yml
│   │
│   ├── docs/                           # 文档（本文件所在目录）
│   │   ├── README.md                   # 本文档
│   │   ├── CHANGELOG.md
│   │   ├── OPS.md
│   │   └── yizhizhu/                   # 开发笔记
│   │
│   ├── assets/                         # 素材
│   ├── demo/                           # 演示
│   ├── logs/                           # 日志
│   │
│   ├── start.sh                        # 一键启动（生产模式）
│   └── dev.sh                          # 开发模式启动
│
└── ...                                 # CLI 相关文件
```

---

## 🖥️ 前端指南

### 页面路由

前端没有使用 React Router，通过 `activeNav` 状态做条件渲染：

| 路由/导航 | 组件 | 说明 |
|----------|------|------|
| `/`（未登录） | LandingPage | 产品首页，介绍+功能+CTA |
| `/login`（未登录） | Login | 登录/注册，支持密码和 TOTP |
| **Team**（已登录） | TeamPage | 团队需求看板（默认首页） |
| **Assets**（已登录） | AssetLibrary | 代码资产库，支持团队筛选 |
| **AI Tools**（已登录） | MainPage | 输入需求、AI 生成代码、安全报告 |
| **Expert Review**（已登录） | ReviewPage | 提交/查看专家审核（含 Stripe 支付） |
| **Settings**（已登录） | SettingsPage | API Key、主题、个人资料 |
| **Admin Panel**（已登录） | AdminPage | 代码审核 + 用户管理 + 数据浏览器（仅 admin 可见） |

### 主要交互

1. **生成代码**：AI Tools 中描述需求 → 选择 Provider/Model → Generate → SSE 流式输出代码 + 自动扫描
2. **安全质量报告**：双仪表盘（Security + Quality），代码质量问题逐项列出（复杂度/死代码/嵌套等）
3. **保存资产**：生成后点击保存 → 自动 SHA256 去重 → 团队共享
4. **专家审核**：输入 Task ID + 备注 → 提交 → 管理员在 8002 端口审核 → 用户展开卡片看 Verdict + Report

### 状态管理

- 全部使用 React Context + useState
- 认证状态：localStorage（`nexus-auth-token`、`nexus-auth-role`）
- 设置持久化：localStorage + 后端双向同步
- 主题持久化：localStorage（CSS 变量注入 `document.documentElement`）

### 主题系统

5 种预设主题色，通过 CSS 自定义属性驱动：

| 主题 | 风格 | 配色 |
|------|------|------|
| Terminal | 绿色荧光 | `#0A0A0A` / `#00FF41` |
| Nexus Default | 深蓝 | `#0D1117` / `#22D3EE` |
| Dracula | 深紫 | `#282A36` / `#BD93F9` |
| GitHub Light | 浅色 | `#F6F8FA` / `#0969DA` |
| Monokai | 经典 | `#1E1E1E` / `#A6E22E` |

---

## 🔌 后端 API 参考

所有 API 前缀为 `/api/v1`，认证方式为 JWT Bearer Token。

### 核心功能

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/generate` | **需求→代码生成** — 输入自然语言，AI 生成代码，自动安全扫描 | 必须 |
| GET | `/generate/tasks` | 列出当前用户的生成任务 | 必须 |
| GET | `/generate/tasks/{id}` | 获取特定任务详情（代码 + 扫描报告） | 必须 |
| POST | `/scan` | **独立代码扫描** — 粘贴代码即扫，支持 python/js/go/cpp | 必须 |
| GET | `/scan/tasks/{id}` | 获取某个任务的扫描报告 | 必须 |
| GET | `/scan/history` | 扫描历史 | 必须 |
| POST | `/review/submit` | **提交专家审核** — 付费找真人审查代码 | 必须 |
| GET | `/review/my-requests` | 查看自己的审核请求 | 必须 |
| GET | `/review/pending` | (Admin) 待审核列表 | admin |
| PUT | `/review/{id}/decide` | (Admin) 给出审核结论 | admin |
| GET | `/review/all` | (Admin) 全部审核记录 | admin |
| POST | `/assets` | **保存代码到资产库**（自动去重） | 必须 |
| GET | `/assets` | 列出资产（支持筛选） | 必须 |
| DELETE | `/assets/{id}` | 删除资产 | 必须 |
| POST | `/assets/check-similar` | 检测新需求是否与已有资产相似 | 必须 |
| POST | `/payment/create-checkout-session` | **创建 Stripe 支付** — 为审核付费 | 必须 |
| GET | `/payment/config` | 获取支付配置（价格、是否已配 Stripe） | 必须 |
| POST | `/payment/webhook` | Stripe Webhook 回调 | 无需认证 |

### 认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/auth/login` | 密码或 TOTP 登录 | 无 |
| GET | `/auth/verify` | 验证 JWT 有效性 | 可选 |
| GET/POST | `/auth/me` | 获取当前用户信息 | 必须 |
| POST | `/auth/register` | 注册新用户 | 无 |
| POST | `/auth/logout` | 注销，吊销 session | 必须 |
| POST | `/auth/refresh` | 无感刷新 JWT | 必须 |
| POST | `/auth/change-password` | 修改密码 | 必须 |

### AI 聊天

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/chat/completions` | AI 推理代理（SSE 流式），支持 5+ provider | 可选 |
| GET | `/chat/sessions` | 聊天会话列表 | 必须 |
| POST | `/chat/sessions` | 创建新会话 | 必须 |
| GET | `/chat/sessions/{id}/messages` | 获取消息列表 | 必须 |
| POST | `/chat/sessions/{id}/messages` | 添加消息 | 必须 |
| POST | `/chat/share` | 分享对话 | 必须 |
| GET | `/chat/search` | 搜索聊天记录 | 必须 |

### 系统

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 无 |
| GET | `/version` | 版本信息 | 无 |
| GET | `/system/status` | 系统资源（CPU/内存） | 无 |
| GET | `/admin/users` | (Admin) 用户列表 | admin |
| PUT | `/admin/users/{id}/role` | (Admin) 修改角色 | admin |
| DELETE | `/admin/users/{id}` | (Admin) 删除用户 | admin |
| GET | `/admin/stats` | (Admin) 系统统计 | admin |
| GET | `/settings` | 获取用户设置 | 必须 |
| PUT | `/settings` | 更新用户设置 | 必须 |

---

## 🗄️ 数据库

项目使用 **单个 SQLite 数据库** `app.db`，位于 `backend/data/`。

> ⚡ 已将原本分散的 `auth.db` 和 `chat_history.db` 合并到 `app.db`。首次启动会自动迁移遗留数据，迁移完成后旧文件可安全删除。

### `app.db` — 统一数据库

| 表 | 说明 | 关键字段 |
|----|------|---------|
| `users` | 用户账号 | id, username, password_hash, role, totp_secret |
| `sessions` | JWT 会话 | id, user_id, token_jti, expires_at |
| `settings` | 用户设置（JSON） | user_id, settings_json |
| `generation_tasks` | AI 生成任务 | id, user_id, idea_text, generated_code, status |
| `scan_results` | 安全扫描结果 | id, task_id, overall_score, verdict, report_json |
| `code_assets` | 代码资产（含去重） | id, user_id, title, code_hash, language, team_id |
| `review_requests` | 专家审核请求 | id, user_id, task_id, status, admin_verdict |
| `teams` | 团队 | id, name, invite_code, created_by |
| `team_members` | 团队成员 | team_id, user_id, role |
| `feature_requests` | 需求 | id, team_id, title, status |
| `chat_sessions` | AI 聊天会话 | id, user_id, title |
| `chat_messages` | AI 聊天消息 | id, session_id, role, content |

---

## 🔐 安全扫描引擎

这是平台的核心差异化功能。位于 `backend/app/scanner/`。

### 支持语言

| 语言 | 扫描方式 | 检测能力 |
|------|---------|---------|
| **Python** | AST 分析 + 正则 | 完整 — 危险函数、SQL注入、敏感泄露 |
| **JavaScript** | 正则匹配 | 危险函数、XSS风险、网络请求 |
| **Go** | 正则匹配 | 命令执行、数据库连接、网络操作 |
| **C++** | 正则匹配 | 缓冲区溢出、命令执行、不安全函数 |

### 检测分类

| 类别 | 严重程度 | 示例 |
|------|---------|------|
| 🔴 危险函数调用 | Critical/High | `eval()`, `exec()`, `os.system()`, `subprocess` |
| 🟠 SQL 注入 | High | 字符串拼接 SQL、f-string 拼接 |
| 🟠 API Key 泄露 | High | 代码中硬编码 `sk-xxx`、`api_key: "xxx"` |
| 🟠 硬编码密码 | High | `password = "xxx"`, `secret = "xxx"` |
| 🔴 私钥泄露 | Critical | `-----BEGIN PRIVATE KEY-----` |
| 🟡 敏感操作 | Medium | `open()`、`os.remove()`、`fetch()`、socket |
| 🔵 最佳实践 | Low/Info | 内存管理、F-string、字符串格式化 |

### 评分系统

```
无问题     → Score: 0   → ✅ Safe
1-2 个中低 → Score: 1-20  → 🟡 Minor
3+ 中高    → Score: 30+  → 🟠 Needs Review
高/严重    → Score: 60+  → 🔴 Dangerous
```

### 报告包含

每份扫描报告包含：
1. **总体裁定** — Safe / Minor / Needs Review / Dangerous + 一句话说明
2. **分数仪表盘** — 0-100 环形图
3. **代码行为描述** — "What this code does"（非技术人员能看懂）
4. **发现项列表** — 每个问题含：风险等级、标题、说明、行号、代码片段、**修改建议**

---

## 👥 专家审核流程

审核是平台的商业模式。

### 用户视角

1. 生成代码 → 查看安全报告 → 仍不放心
2. 点击 "Request Expert Review" 或去 **Expert Review** 页面
3. 输入 Task ID + 备注 → 提交
4. 等待管理员审核
5. 在 **Expert Review** 页面查看结果

### 管理员视角

1. 登录 admin 账号 → 进入 **Admin Panel**
2. **Pending Reviews** 标签显示所有待审核请求
3. 点击展开 → 查看代码 + 用户备注
4. 填写反馈 → 选择 **Approve / Request Changes / Reject**
5. 用户会看到审核结论和反馈

---

## 🐳 部署

### Docker Compose（推荐）

```bash
cd deploy
docker compose up -d
```

包含两个服务：
- **backend**: FastAPI 服务 (:8000)
- **frontend**: Vite 开发服务器 (:5173)

### 生产部署

参考 `deploy/` 目录下的 Nginx 配置和 setup 脚本：
- Nginx 反向代理前端静态文件 + 后端 API
- SSL 证书配置
- 系统服务（systemd）管理

### 环境变量

在 `backend/.env` 中配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | `change-me` | JWT 签名密钥（生产环境务必修改） |
| `DEBUG` | `true` | 调试模式，生产设为 `false` |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `CORS_ORIGINS` | `http://localhost:5173` | 跨域允许的域名 |
| `SITE_URL` | `http://localhost:5173` | 站点 URL（Stripe 回调用） |
| `STRIPE_SECRET_KEY` | `sk_live_...` | （可选）激活 Stripe 支付 |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_...` | Stripe 公钥 |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Stripe Webhook 签名密钥 |
| `PAYMENT_PRICE_USD` | `999` | 每次审核价格（美分） |

### Cloudflare Tunnel

`start.sh` 会自动读取 `backend/.env` 中的 `TUNNEL_TOKEN` 启动 Cloudflare Tunnel，将本地服务暴露到 `trufflekit.com`。

---

## 🛠️ 技术栈

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.x | UI 框架 |
| TypeScript | 5.6 | 类型安全 |
| Vite | 6.x | 构建工具 + 开发服务器 |
| Tailwind CSS | 3.x | CSS 框架 |
| Vitest | 4.x | 单元测试 |

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| FastAPI | 0.115+ | Web 框架 |
| Uvicorn | - | ASGI 服务器 |
| SQLite | - | 数据库（无需额外安装） |
| httpx | 0.28+ | 异步 HTTP（AI API 代理） |
| PyJWT | - | JWT 令牌 |
| pyotp | - | TOTP 双因子认证 |
| psutil | 5.9+ | 系统资源监控 |

---

## ❓ 常见问题

### Q: 为什么 AI 生成代码失败？

最常见原因是 **没有配置 API Key**。去 Settings → API Keys 填入你的 OpenAI / DeepSeek / Anthropic 等密钥。

### Q: 支持哪些 AI 模型？

通过配置不同 provider 的 API Key，支持：
- **OpenAI** — GPT-4o, GPT-4, GPT-3.5
- **Anthropic** — Claude 3.5 Sonnet, Claude 3 Opus
- **DeepSeek** — DeepSeek V3, DeepSeek R1
- **OpenRouter** — 聚合 200+ 模型
- **Ollama** — 本地部署的开源模型

### Q: 代码生成和 AI 聊天有什么区别？

- **Generate（生成）**：使用专门优化过的 system prompt（非对话模式），温度 0.3，生成完整可运行的代码 + 自动安全扫描
- **Chat（聊天）**：通用对话模式，支持流式 SSE，可连续对话

### Q: 怎么判断代码安不安全？

每次生成后，系统会**自动执行安全扫描**并展示 **SafetyReport**。你可以看到：
- 总体安全评分（0-100）
- "What this code does" — 这段代码做了什么事（中文/英文）
- 每个安全问题的位置、说明和修改建议
- 如果不放心，可以提交给人工专家审核

### Q: 数据库在哪里？

单个 SQLite 文件 `backend/data/app.db`。删除它再重启会自动重建（包括 admin 用户）。

### Q: 日志文件在哪里？

所有日志统一在 `website/logs/` 下：
- `backend-app.log` — Python 应用运行日志
- `backend-uvicorn.log` — 后端服务启动日志
- `frontend-dev.log` — 前端开发服务器日志
- `frontend-build.log` — 前端构建日志
- `tunnel.log` — Cloudflare Tunnel 日志

### Q: 如何创建其他管理员账号？

用 admin 登录 → **Admin Panel** → **Users** 标签页 → 找到相应用户 → 下拉选择 "admin"。

### Q: TOTP 双因子认证怎么用？

1. 登录后去 Settings → 暂无 TOTP 设置 UI
2. 可以通过 API 调用 `POST /api/v1/auth/totp/setup` 获取密钥

---

## ✅ 功能状态一览

### 认证系统

| 功能 | 状态 |
|------|------|
| 密码注册/登录 | ✅ |
| JWT 令牌管理 (24h + refresh) | ✅ |
| TOTP 双因子认证 | ✅ |
| 修改密码 | ✅ 后端就绪，前端有接口 |
| 删除账号 | ✅ 后端就绪 |
| OAuth 连接 | ❌ Mock 实现，无真实 OAuth |

### 团队管理

| 功能 | 状态 |
|------|------|
| 创建/加入/离开/解散团队 | ✅ |
| 多团队支持 (顶部下拉切换) | ✅ |
| 成员角色管理 (owner/reviewer/member) | ✅ |
| 邀请码 (仅 owner 可见) | ✅ |
| Dashboard 多团队摘要 | ✅ |

### 需求看板

| 功能 | 状态 |
|------|------|
| 提交需求、列表、详情展开 | ✅ |
| 6 种状态标识 | ✅ |
| **提交时自动查重** (SequenceMatcher >40%) | ✅ |
| 审核批准/拒绝/标记重复 | ✅ |
| 审核后一键关联生成任务 | ✅ |

### AI 代码生成

| 功能 | 状态 |
|------|------|
| 自定义需求生成 + 6 业务模板 | ✅ |
| 4 语言 (Python/JS/Go/C++) | ✅ |
| 多模型 (OpenAI/DeepSeek/Anthropic/OpenRouter) | ✅ |
| 生成后自动安全扫描 | ✅ |

### 安全扫描

| 功能 | 状态 |
|------|------|
| 粘贴代码独立扫描 (无需 Key) | ✅ |
| 4 语言检测 + 危险函数/SQL注入/敏感泄露 | ✅ |
| 人类可读报告 + ScoreGauge 仪表盘 | ✅ |
| 修复建议 | ✅ |
| 项目级 ZIP 扫描 | 🔴 未实现 |

### 代码资产库

| 功能 | 状态 |
|------|------|
| SHA256 去重保存 | ✅ |
| 列表/搜索/语言筛选/团队筛选 | ✅ |
| 相似度检测 | ✅ |

### 专家审核 + 支付

| 功能 | 状态 |
|------|------|
| 提交审核、查看、管理员决定 | ✅ |
| Stripe Checkout 支付 | ⚠️ 代码就绪，需配置 `STRIPE_SECRET_KEY` |
| 定价模型 | 💲 预设 $9.99/次，环境变量可调 |

### 管理后台

| 功能 | 状态 |
|------|------|
| 审核面板 (Pending/History) | ✅ |
| 用户管理 (列表/角色/删除) | ✅ |

### 首页

| 功能 | 状态 |
|------|------|
| 公开 Landing Page (`/`) | ✅ |
| 登录页 (`/login`) | ✅ |
| 无团队引导创建 | ✅ |

### PWA

| 功能 | 状态 |
|------|------|
| Service Worker 离线缓存 | ✅ |
| manifest + 手机添加到主屏幕 | ✅ |
| 全屏沉浸模式 | ✅ |

### 通知系统

| 功能 | 状态 |
|------|------|
| 审核结果自动通知 (站内) | ✅ |
| 铃铛图标 + 红点 badge | ✅ |
| 下拉通知面板 + 全部已读 | ✅ |
| 邮件/推送通知 | 🔴 未实现 |

### 引导导览

| 功能 | 状态 |
|------|------|
| 5 步分步导览 (GuidedTour) | ✅ |
| 中英文双语 | ✅ |
| 上一步/跳过/完成 | ✅ |

---

## 📝 关于项目

Truffle AI Platform 是对原本 Nexus AI v1 的大规模重构，砍掉了团队聊天、项目管理、文件 IDE 等冗余功能，聚焦于 **需求→审核→生成→资产** 协作流程。

### 相比 v1 删除的内容

| 删除项 | 原因 |
|-------|------|
| 团队聊天（TeamChat） | 不做 IM，打不过飞书/微信 |
| 团队管理（TeamPanel） | MVP 阶段不需要 |
| 项目管理（Projects） | 简陋 CRUD，打不过 Jira |
| 文件 IDE（IDE） | 目标用户不写代码 |
| 日报 Digest | 跟核心场景无关 |
| C++ 引擎 | 非核心功能，技术炫技 |
| OAuth 连接 | MVP 不需要 |
| 国际化 i18n | 只做英文 |
| 大部分主题设置 | 保留 5 套预设即可 |
