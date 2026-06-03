# Truffle Code Map — 代码模块速查手册

> **项目**: Truffle — 面向小团队的"需求→审核→开发→资产"协作平台
> **前端**: `Nexus AI/` (Vite + React + TypeScript + Tailwind)
> **后端**: `platform-backend/` (FastAPI + Python)
>
> 出问题先查这里，直接定位到要改的文件。

---

## 目录

- [认证系统 (Auth)](#1-认证系统-auth)
- [团队管理 (Team)](#2-团队管理-team)
- [需求看板 (Feature Requests)](#3-需求看板-feature-requests)
- [AI 代码生成 (Generate)](#4-ai-代码生成-generate)
- [安全扫描 (Scan)](#5-安全扫描-scan)
- [资产库 (Assets)](#6-资产库-assets)
- [代码沙箱 (Compile)](#7-代码沙箱-compile)
- [专家审核 (Review)](#8-专家审核-review)
- [设置 (Settings)](#9-设置-settings)
- [管理后台 (Admin)](#10-管理后台-admin)
- [聊天 (Chat)](#11-聊天-chat)
- [导出 (Export)](#12-导出-export)
- [前端框架 (UI)](#13-前端框架-ui)
- [i18n 语言系统](#14-i18n-语言系统)
- [部署 / 运维](#15-部署--运维)
- [数据库](#16-数据库)

---

## 1. 认证系统 (Auth)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/auth/auth.py` | **核心认证逻辑** — 注册、登录(密码/TOTP)、JWT签发/验证、Session管理、OAuth连接 |
| `platform-backend/app/auth/__init__.py` | 包初始化 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/LandingPage.tsx` | 🆕 产品首页 (`/`) — Hero、功能、引导 |
| `Nexus AI/src/components/Login.tsx` | 登录/注册页面 UI（密码登录、TOTP 六位码、注册表单） |
| `Nexus AI/src/App.tsx` | 登录状态管理、token 验证、路由分发 (`/` → Landing, `/login` → Login) |

### 数据流向

```
用户输入 → Login.tsx → POST /api/v1/auth/login
                       → auth.py: login()
                       → 验证密码/TOTP → 签发 JWT
                       → 返回 access_token
                       → 前端存 localStorage('nexus-auth-token')
```

### 常见问题排查

| 问题 | 可能原因 | 检查位置 |
|------|---------|---------|
| 登录返回 401 | 密码错误 / 用户不存在 | `auth.py:238-241` verify_password |
| TOTP 登录失败 | secret 不匹配 / 时间偏差 | `auth.py:247-251` TOTP verify |
| 登录后马上 401 | JWT 过期(24h) / session 被删 | `auth.py:156-163` is_session_active |
| 注册失败 | 用户名重复 / 密码太短 | `auth.py:373-395` register |
| invite_code 无效 | 团队不存在 / code 错误 | `auth.py:387-392` 验证逻辑 |
| Token 刷新失败 | refresh 接口问题 | `auth.py:311-327` refresh_token |

---

## 2. 团队管理 (Team)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/team.py` | **全部团队 API** — CRUD、成员管理、需求提交/审核/生成 |
| `platform-backend/app/db.py` | teams / team_members / feature_requests 表定义 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/TeamPage.tsx` | **团队页面完整 UI** — 团队切换、需求看板、成员管理、邀请码、创建/加入/解散 |
| `Nexus AI/src/components/MainPage.tsx` | 首页团队活动摘要 |
| `Nexus AI/src/components/Sidebar.tsx` | 侧边栏 "Team" 导航项 |

### API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/team/create` | 创建团队 |
| GET | `/api/v1/team/list` | 我的团队列表 |
| GET | `/api/v1/team/my` | 团队详情(成员、邀请码) |
| POST | `/api/v1/team/join` | 加入团队(邀请码) |
| POST | `/api/v1/team/regenerate-invite` | 重新生成邀请码(owner) |
| POST | `/api/v1/team/disband` | 解散团队(owner) |
| POST | `/api/v1/team/leave` | 离开团队(非owner) |
| POST | `/api/v1/team/change-role` | 修改成员角色(owner) |
| POST | `/api/v1/team/requests` | 提交需求 |
| GET | `/api/v1/team/requests` | 列出团队需求 |
| PUT | `/api/v1/team/requests/{id}/review` | 审核需求(reviewer) |
| POST | `/api/v1/team/requests/{id}/generate` | 为需求创建生成任务(reviewer) |
| POST | `/api/v1/team/requests/{id}/link-task` | 关联已完成的任务 |

### 常见问题排查

| 问题 | 可能原因 | 检查位置 |
|------|---------|---------|
| 无法创建团队 | 名称空白 / 数据库无权限 | `team.py:81-104` create_team |
| 邀请码无效 | 代码过期 / 打错了 | `team.py:178-201` join_team |
| 角色没生效 | 数据库写入失败 | `team.py:272-306` change_role |
| 需求提交后不显示 | team_id 不对 / 权限问题 | `team.py:316-342` create_request |
| 审核按钮不出来 | role 不是 reviewer/owner | `team.py:464-466` 验证 |
| 团队切换无效 | selectedTeamId 状态不对 | `TeamPage.tsx:150-152` handleSwitchTeam |

---

## 3. 需求看板 (Feature Requests)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/team.py` | create_request, list_requests, get_request, review_request (见上) |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/TeamPage.tsx` | 需求卡片列表、展开/折叠、审核操作、生成代码 |
| `Nexus AI/src/components/MainPage.tsx` | 首页最近需求摘要 |

### 相关数据库表

- `feature_requests` — 字段: id, team_id, user_id, title, description, status, linked_task_id, duplicate_of, reviewer_notes

### 状态流转

```
pending → approved → generating → completed
pending → rejected
pending → duplicate
```

---

## 4. AI 代码生成 (Generate)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/generate.py` | **AI 生成核心** — 接收 idea → 调 AI provider → 返回代码 → 自动安全扫描 |
| `platform-backend/app/scanner/static_analyzer.py` | 安全扫描引擎 |
| `platform-backend/app/scanner/reporter.py` | 扫描报告生成 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/MainPage.tsx` | 生成入口：模板选择、输入框、语言选择、粘贴扫描 |
| `Nexus AI/src/components/Dashboard.tsx` | 生成结果展示：代码预览、安全报告、保存/导出/提交审核 |
| `Nexus AI/src/components/SafetyReport.tsx` | 安全报告可视化组件 |
| `Nexus AI/src/context/SettingsContext.tsx` | API Key 读取、Provider/Model 列表 |

### 数据流向

```
用户在 MainPage 输入 idea
    → Dashboard.handleGenerate()
    → POST /api/v1/generate
    → generate.py: generate_code()
    → _call_ai_provider() 调用 OpenAI/DeepSeek/Anthropic…
    → 收到代码 → scan_code() 自动扫描
    → 返回 { code, scan_result }
    → 前端展示 + SafetyReport
```

### 常见问题排查

| 问题 | 可能原因 | 检查位置 |
|------|---------|---------|
| 生成返回 400 "API key required" | 没配置 API Key | `generate.py:77-79` |
| 生成卡住然后超时 | AI provider 不可达 / 网络问题 | `generate.py:282-319` _call_ai_provider |
| 生成的代码全是 markdown | AI 没遵守 prompt 规则 | `generate.py:323-342` _clean_code_block |
| 安全报告显示 0 issues | 扫描没发现问题 | `static_analyzer.py` |
| 模型选择没效果 | provider/model 映射不对 | `generate.py:244-256` _call_ai_provider |
| 前端报 "Network error" | fetch 失败 / CORS | `Dashboard.tsx:101` catch |

---

## 5. 安全扫描 (Scan)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/scanner/static_analyzer.py` | **扫描引擎** — Python AST + 所有语言正则检测 |
| `platform-backend/app/scanner/reporter.py` | 报告生成 (评分、摘要、Verdict) |
| `platform-backend/app/api/scan.py` | 扫描 API（独立粘贴扫描 + 任务扫描历史） |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/SafetyReport.tsx` | 安全报告展示组件 (ScoreGauge、问题列表) |
| `Nexus AI/src/components/MainPage.tsx` | 粘贴扫描入口 |

### 检测能力

| 检测类别 | 语言 | 位置 |
|---------|------|------|
| 危险函数 (eval, exec) | Python (AST) | `static_analyzer.py:42-69` |
| Shell 命令 (os.system, subprocess) | Python | `static_analyzer.py:49-54` |
| SQL 注入 | Python | `static_analyzer.py:89-94` |
| API Key/密码硬编码 | 全部 | `static_analyzer.py:71-87` |
| 私钥泄露 | 全部 | `static_analyzer.py:79-80` |
| XSS 风险 | JavaScript | `static_analyzer.py:302-313` |
| 缓冲区溢出 | C++ | `static_analyzer.py:323-335` |

---

## 6. 资产库 (Assets)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/assets.py` | **资产 CRUD** — 保存/列表/删除/相似度检测 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/AssetLibrary.tsx` | 🆕 资产库页面（搜索、语言筛选、团队筛选、删除） |
| `Nexus AI/src/components/Dashboard.tsx` | 生成结果 → "保存到资产库" 按钮 |

### API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/assets` | 保存资产（自动 SHA256 去重） |
| GET | `/api/v1/assets` | 列表(支持 language/search/team_id 筛选) |
| DELETE | `/api/v1/assets/{id}` | 删除资产 |
| POST | `/api/v1/assets/check-similar` | 相似度检测 |

---

## 7. 代码沙箱 (Compile)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/compile.py` | **代码编译运行** — subprocess 调用 g++/python3/go/node |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/Dashboard.tsx` | "Preview" 标签页 → 编译运行 |

### 语言配置

```python
# compile.py:43-67
COMPILERS = {
    "cpp":    { compile: "g++ -std=c++20", run: "./output" },
    "python3": { run: "python3" },   # 直译
    "go":     { compile: "go build", run: "./output" },
    "javascript": { run: "node" },  # 直译
}
```

### 常见问题排查

| 问题 | 可能原因 | 检查位置 |
|------|---------|---------|
| 编译返回 401 | 未传 JWT (已修复需认证) | `compile.py:87` get_current_user |
| 编译超时 | 代码死循环 / 15s 限制 | `compile.py:69` TIMEOUT |
| 编译返回 "command not found" | 本地没装 g++/node/go | `compile.py:31-38` _find_binary |

---

## 8. 专家审核 (Review)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/review.py` | 审核 CRUD — 提交、我的请求、管理员待审、决定 |
| `platform-backend/app/api/payment.py` | 🆕 Stripe 支付 — 创建 Checkout Session、Webhook、定价配置 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/ReviewPage.tsx` | 用户提交审核 + 查看审核状态 + Stripe 支付按钮 |
| `Nexus AI/src/components/AdminPage.tsx` | 管理员面板 — 审核标签 + 🆕 用户管理标签(角色/删除) |

---

## 9. 设置 (Settings)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/settings.py` | 设置 CRUD、个人资料管理、头像上传、Session 管理 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/SettingsPage.tsx` | 设置页面 UI (API Keys 配置 + 个人资料 + 主题) |
| `Nexus AI/src/context/SettingsContext.tsx` | Settings Context (API Key 读取、Provider/Model) |
| `Nexus AI/src/context/ThemeContext.tsx` | 主题管理 (5 套预设) |

### 注意

API Key 只保存在浏览器 `localStorage`，不再发往后端。

---

## 10. 管理后台 (Admin)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/admin.py` | 用户管理(列表/角色/删除)、统计数据 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/AdminPage.tsx` | 管理面板 UI — 待审核列表 + 审核历史 |

### 注意

`admin` 角色是全局角色(不是团队 owner)，用于管理整个平台的专家审核流程。

---

## 11. 聊天 (Chat)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/chat.py` | AI 聊天代理 — 支持 5+ provider、SSE 流式 |
| `platform-backend/app/api/chat_history.py` | 聊天会话/消息 CRUD、搜索、分享 |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| (聊天 UI 在 Dashboard 中通过 SettingsContext 调用) | |

---

## 12. 导出 (Export)

### 后端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `platform-backend/app/api/export.py` | ZIP 导出 — 代码 + Dockerfile + README + docker-compose.yml |

### 前端文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/components/Dashboard.tsx` | "Download ZIP" 按钮 |

### 语言支持

| 语言 | 生成文件 |
|------|---------|
| Python | main.py, requirements.txt, Dockerfile, docker-compose.yml |
| JavaScript | index.js, package.json, Dockerfile |
| Go | main.go, go.mod, Dockerfile |
| C++ | main.cpp, CMakeLists.txt, Dockerfile |

---

## 13. 前端框架 (UI)

### 核心文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/App.tsx` | **根组件** — 登录状态判断、路由分发 |
| `Nexus AI/src/components/Dashboard.tsx` | **主框架** — 侧边栏布局、子页面渲染、生成逻辑、编译预览 |
| `Nexus AI/src/components/Sidebar.tsx` | 侧边栏导航 + 语言切换 + 登出 |
| `Nexus AI/src/lib/api.ts` | **共享工具** — authHeaders() 等 |

### Contexts

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/context/ThemeContext.tsx` | 5 套主题色管理 + 字体缩放 |
| `Nexus AI/src/context/SettingsContext.tsx` | API Key + Provider/Model 列表 |
| `Nexus AI/src/context/ToastContext.tsx` | Toast 通知系统 |
| `Nexus AI/src/context/LanguageContext.tsx` | i18n 语言切换 |

---

## 14. i18n 语言系统

### 文件

| 文件路径 | 负责内容 |
|---------|---------|
| `Nexus AI/src/lib/translations.ts` | **全部翻译键值对** — 英/中 双语, ~200 键 |
| `Nexus AI/src/context/LanguageContext.tsx` | LanguageProvider + useT() hook |

### 使用方法

```tsx
import { useT } from '../context/LanguageContext'

function MyComponent() {
  const { t, lang, setLang } = useT()
  return <div>{t('sidebar.team')}</div>   // → "Team" / "团队"
}
```

### 添加新翻译

1. 在 `translations.ts` 的 EN 对象和 ZH 对象中各加一条
2. 组件中用 `t('my.new.key')` 引用
3. 如果 key 不存在，fallback 到英文

---

## 15. 部署 / 运维

### 文件

| 文件路径 | 负责内容 |
|---------|---------|
| `start.sh` | **一键启动脚本** — 前端/后端/构建监听 |
| `docker-compose.yml` | Docker 编排 |
| `deploy/nginx.conf` | Nginx 反向代理配置 |
| `deploy/setup.sh` | 生产部署脚本 |
| `OPS.md` | **运维手册** — 备份、恢复、日志、排错 |
| `platform-backend/.env` | 环境变量 (SECRET_KEY, DEBUG, CORS) |

### 域名配置

`SITE_DOMAIN` 环境变量控制构建同步目标 (默认 trufflekit.com)

```bash
SITE_DOMAIN=myapp.com ./start.sh --build
```

---

## 16. 数据库

### 文件

| 数据库 | 路径 | 用途 |
|--------|------|------|
| `app.db` | `platform-backend/data/app.db` | **统一数据库** — 全部表 (users, sessions, settings, generation_tasks, scan_results, code_assets, review_requests, teams, team_members, feature_requests, chat_sessions, chat_messages) |

> ⚡ v2.2 已将 `auth.db` 和 `chat_history.db` 合并到 `app.db`。首次启动自动迁移，旧文件可安全删除。

### 表结构

#### `app.db` — `users`
```
id, username, email, totp_secret, display_name, avatar_url,
password_hash, role, created_at, updated_at
```

#### `app.db` — `teams`
```
id, name, description, invite_code, created_by, created_at
```

#### `app.db` — `feature_requests`
```
id, team_id, user_id, title, description, status,
linked_task_id, duplicate_of, reviewer_notes, created_at, updated_at
```

#### `app.db` — `code_assets`
```
id, user_id, title, description, language, code_hash, source_task_id, team_id, created_at
```

#### `app.db` — `chat_sessions` / `chat_messages`
```
chat_sessions: id, title, user_id, created_at, updated_at
chat_messages: id, session_id, role, content, created_at
```

---

## 快速诊断索引

### 问题 → 检查文件

| 现象 | 优先检查 3 个文件 |
|------|-----------------|
| 页面白屏 / 报错 | `App.tsx` → `ErrorBoundary.tsx` → 对应组件 |
| 登录/注册问题 | `Login.tsx` → `auth.py` → 网络请求 |
| 团队页面奇怪 | `TeamPage.tsx` → `team.py` → `FeatureRequest` 数据结构 |
| AI 生成不了 | `Dashboard.tsx:handleGenerate` → `generate.py` → API Key 配置 |
| 安全扫描结果不对 | `SafetyReport.tsx` → `static_analyzer.py` → `reporter.py` |
| 代码保存不了 | `Dashboard.tsx:handleSaveToAssets` → `assets.py` |
| 编译/预览报错 | `Dashboard.tsx:handleRunPreview` → `compile.py` |
| 导航/侧栏问题 | `Sidebar.tsx` → `Dashboard.tsx:activeNav` |
| 语言切换不生效 | `LanguageContext.tsx` → `translations.ts` → 对应组件 |
| 数据库错误 | `db.py` → 对应 API 文件 → `platform-backend/data/app.db` |
