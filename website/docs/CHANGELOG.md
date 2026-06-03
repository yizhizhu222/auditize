# Changelog

## 2026-06-02 — v2.14 缓存修复 + PWA 激活策略

### 修复

| 问题 | 说明 |
|------|------|
| **PWA Service Worker 不更新** | 浏览器缓存了旧 SW，部署新版本后用户看不到最新内容 |
| **Cloudflare CDN 缓存** | CDN 边缘节点缓存 index.html，用户一直看到旧版 |
| **更新不自动接管** | SW 检测到更新但不立即激活，需要关闭标签页重开 |

### 修复方案

| 层面 | 改动 |
|------|------|
| **后端响应头** | `index.html` / `sw.js` / `workbox-*.js` 全部返回 `Cache-Control: no-cache, no-store, must-revalidate` + `CDN-Cache-Control: no-cache` |
| **PWA 构建** | `skipWaiting: true` + `clientsClaim: true`，新 SW 立即接管所有标签页 |
| **SW 注册** | `injectRegister: 'inline'` 将注册脚本嵌入 HTML，避免外部缓存 |
| **前端监控** | `App.tsx` 监听 SW `updatefound`→`activated` 事件，自动刷新页面 |
| **页面 Focus** | 用户切回标签页时自动检查 SW 更新 |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/main.py` | 🔧 所有 HTML/SW 响应添加 no-cache 头 + CDN-Cache-Control |
| `Nexus AI/vite.config.ts` | 🔧 新增 `skipWaiting` + `clientsClaim` + `injectRegister: 'inline'` |
| `Nexus AI/src/App.tsx` | 🔧 新增 SW 更新监听 + 页面 focus 自动检测 |
| `Nexus AI/index.html` | 🔧 添加 `Cache-Control` / `Pragma` / `Expires` meta 标签 |

---

## 2026-06-02 — v2.13 侧边栏修复 + Expert Review 入口开放

### 修复

**普通用户 (role=user) 侧边栏看不到 Expert Review 入口**
`Sidebar.tsx` 中 `isMember = (role === 'user')` 分支隐藏了 `reviews` 导航项，只有 reviewer/owner 角色才能看到。所有用户提交审核后无法通过侧边栏进入查看回复。

### 改动

- `Sidebar.tsx`: 移除角色分支判断，**所有用户统一显示全部导航项**（Team / AI Tools / Assets / Reviews / Settings / History）
- 去掉了 `isMember`/`else` 分支逻辑，简化为同一套 navItems

---

## 2026-06-02 — v2.12 审核报告展示修复

### 修复

专家回复后用户看不到代码分析报告和代码原文。ReviewPage 只显示了 verdict 和 feedback 文字。

### 改动

| 端 | 改动 |
|----|------|
| **后端** `review.py` | `my-requests` 接口新增返回 `code`（生成代码）和 `scan_report`（安全+质量分析报告），已完成的审核自动关联 scan_results |
| **前端** `ReviewPage.tsx` | 审核卡片改为可展开，完成状态显示：Expert Verdict + Code Analysis Report (SafetyReport) + Generated Code |
| **翻译** `translations.ts` | 补充 `replyOn`、`changes_needed`、`pending_payment` 中英翻译 |

---

## 2026-06-02 — v2.11 Landing Page 重构

### 新增模块

| 模块 | 内容 |
|------|------|
| **统计栏** | 4+ Languages / 15+ Quality Checks / 6 Templates / Zero Platform Fees |
| **功能扩展** | 从 3 个 Feature 扩展到 6 个（新增 Expert Review / Team Collaboration / Asset Library） |
| **Scanner 展示** | 伪终端窗口展示代码质量检测的真实输出示例 |
| **定价方案** | 三级定价卡：Free $0 / Team $0 (Popular) / Enterprise Custom |
| **合作联系** | 📧 `cjwd1234cjwd@163.com` + 合作 / 定制开发 / 反馈三个入口 |
| **FAQ** | 6 个可展开常见问题 |
| **四栏 Footer** | Brand / Product / Resources / Contact 分栏布局 |
| **动画系统** | 滚动渐入（IntersectionObserver）、Hero 逐元素淡入、按钮 hover 缩放、返回顶部悬浮按钮 |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `Nexus AI/src/components/LandingPage.tsx` | 🔄 重写 — 增加 7 个新 section，统计栏/定价/FAQ/合作等 |
| `Nexus AI/src/index.css` | 🔧 新增 `fadeIn` / `fadeInUp` / `pulseGlow` 关键帧动画 |

---

## 2026-06-02 — v2.10 代码质量检测引擎

### 新增功能

| 检测项 | 风险等级 | 说明 |
|--------|----------|------|
| **圈复杂度** | 🔴 高 | 函数分支/条件过多（≥10 警告，≥15 严重） |
| **函数过长** | 🟠 中 | 超过 60 行警告，100 行严重 |
| **空异常处理** | 🔴 高 | `except: pass` 无声吞掉错误 |
| **参数过多** | 🟠 中 | 超过 10 个参数 |
| **未使用变量** | 🔵 低 | 赋值但从未使用 |
| **嵌套过深** | 🔴 高 | 缩进 ≥6 层 |
| **死代码** | 🟠 中 | `return`/`raise` 后的不可达代码 |
| **多余 else** | 🔵 低 | `if` 已 `return` 时 `else` 可去掉 |
| **Magic Number** | 🔵 低 | 未命名的数字常量 |
| **TODO/FIXME** | 🔵 低 | 未完成的标记 |
| **裸 except:** | 🟠 中 | 捕获所有异常（含 SystemExit） |
| **变量遮蔽** | 🔵 低 | 局部变量覆盖内置函数名 |
| **过多 return** | 🟠 中 | 超过 5 个出口点 |
| **重复代码块** | 🟠 中 | 4 行以上相同代码多次出现 |
| **命名规范** | ⚪ 信息 | PascalCase/snake_case 违规 |
| **冗余 pass** | ⚪ 信息 | 与其他语句共存的空操作 |

### 架构变化

- `static_analyzer.py` 新增 `CodeQualityAnalyzer` 类（16 项检测）
- `ScanResult` 新增 `quality_score` / `overall_score` / `finding_type` 字段
- `reporter.py` 新增双评分系统（Security + Quality），独立区域展示
- 新质检：`ScanFinding.finding_type = "security" | "quality"`
- 前端 `SafetyReport.tsx` 双仪表盘 + 分开的 Security / Quality 问题区域

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/scanner/static_analyzer.py` | 🔄 重写 — 新增 CodeQualityAnalyzer + 扫描结果扩展 |
| `platform-backend/app/scanner/reporter.py` | 🔄 重写 — 双评分 + 质量板块 + 综合裁决 |
| `Nexus AI/src/components/SafetyReport.tsx` | 🔄 重写 — 双仪表盘 + Code Quality 独立区域 |

---

## 2026-06-02 — v2.9 Token 延长 + 生产端口修复

### 变更

| 项目 | 旧值 | 新值 |
|------|------|------|
| JWT Token 有效期 | 24 小时 | **7 天**（168 小时） |
| 后端端口调整 | 8000（开发）/ 8080（临时）| **8001**（匹配 Cloudflare 隧道配置） |

### 修复

- `ACCESS_TOKEN_EXPIRE_HOURS = 24` → `168`：登录后 7 天内刷新不踢回登录页
- **生产 502 修复**：后端启动在 8080，但 Cloudflare tunnel 指向 8001，端口不匹配导致 `trufflekit.com` 502。修正为统一使用 8001 端口

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/auth/auth.py` | 🔧 `ACCESS_TOKEN_EXPIRE_HOURS = 168` |

---



## 2026-06-02 — v2.8 邮箱验证 + 登录锁定系统

### 新增功能

| 功能 | 说明 |
|------|------|
| **邮箱格式验证** | 注册时自动校验邮箱格式，拦截临时邮箱 |
| **邮箱验证码** | 注册后可发送6位验证码到邮箱，支持任意 SMTP 服务商 |
| **SMTP 邮件发送** | Python 内置 `smtplib`，零额外依赖。未配置时自动降级为日志打印 |
| **登录锁定** | 连续5次密码错误 → 账户锁定15分钟，成功后自动解锁 |
| **登录失败持久化** | `login_attempts` 表，重启不清零 |
| **验证状态 API** | `/api/v1/auth/me` 返回 `email_verified`，Settings 页显示 |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/auth/auth.py` | 🔧 邮箱验证、登录锁定、验证码端点、/me 返回 email_verified |
| `platform-backend/app/email_utils.py` | 🆕 SMTP 邮件发送工具（smtplib），配置缺失降级 |
| `platform-backend/app/db.py` | 🆕 `verification_codes` + `login_attempts` 表 + 字段 |
| `platform-backend/.env` | ➕ SMTP 配置注释 + ADMIN_PASSWORD 注释 |
| `Nexus AI/src/components/Login.tsx` | 🔧 注册后验证码输入界面、验证邮箱模式 |
| `Nexus AI/src/components/SettingsPage.tsx` | 🔧 显示邮箱验证状态、发送/输入验证码 |

### SMTP 配置

在 `platform-backend/.env` 中取消注释并填入：

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your-app-password
```

未配置 SMTP 时验证码打印到服务器日志。

---

## 2026-06-02 — v2.7 安全加固 + Bug 修复大扫除

### 🔴 安全修复

| 严重程度 | 问题 | 文件 | 修复 |
|---------|------|------|------|
| 致命 | Admin 进程读不到 `.env`，`SECRET_KEY` 回退为 `"change-me"` | `admin_app.py:30` | `parent` → `parent.parent`，正确加载 `.env` |
| 高 | CORS 默认值泄漏公网 IP 和废弃 ngrok 域名 | `main.py:112` | 移除 `58.16.61.185` 和 ngrok URL |
| 高 | Admin 密码硬编码 `"admin123"` | `main.py:95` | 改为 `ADMIN_PASSWORD` 环境变量，默认值时打印警告 |
| 高 | 密码用 SHA-256 无迭代，GPU 秒破 | `auth.py:58-61` | 替换为 **bcrypt**，支持旧 SHA-256 哈希无缝迁移 |
| 中 | 密码仅要求 6 位，无复杂度 | `auth.py:333-336` | 改为 **8 位 + 大小写 + 数字** |
| 中 | 登录无任何限速 | `auth.py:172` | 新增内存限速器：60s 内最多 5 次尝试，超限返回 429 |

### 🟠 代码质量修复

| 问题 | 文件 | 修复 |
|------|------|------|
| 前端 16 个文件、所有 `fetch()` 均无超时 | `Nexus AI/src/lib/api.ts` | 新建 `apiFetch()` 封装，默认 **15s 超时**，统一 JSON 解析和错误处理 |
| 静默空 `catch {}` 吞掉网络错误 | 8 个组件 | 全部加上 `console.error()` 日志 |
| `App.tsx` 中 `res.json()` 未检查 `res.ok` | `App.tsx` | 改用 `apiFetch` 自动处理 |
| 日志文件无限增长 | `main.py:60` | `FileHandler` → `RotatingFileHandler`（10MB × 5 份轮转） |
| `PRAGMA foreign_keys=OFF` 异常时不被恢复 | `db.py:347` | `except` → `finally` 确保 `PRAGMA foreign_keys=ON` 一定会执行 |
| PWA runtimeCaching 正则只匹配路径前缀 | `vite.config.ts:31` | 修复为匹配完整 URL |
| PWA 预缓存中 `includeAssets` 与 manifest icons 重复 | `vite.config.ts:11` | 从 `includeAssets` 移除重复的图标文件 |
| PWA 离线无 fallback 页面 | `vite.config.ts` | 新增 `navigateFallback: '/index.html'` |
| `tsconfig` 中 `noUnusedLocals/Parameters` 为 false | `tsconfig.app.json:16-17` | 改为 `true` |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/admin_app.py` | 🔧 `.env` 路径修复 |
| `platform-backend/app/main.py` | 🔧 CORS 默认值清理、admin 密码可配置、日志轮转 |
| `platform-backend/app/db.py` | 🔧 `PRAGMA foreign_keys` finally 保护 |
| `platform-backend/app/auth/auth.py` | 🔧 bcrypt 密码哈希 + 强度校验 + 登录限速 |
| `platform-backend/requirements.txt` | ➕ `bcrypt>=4.2.0` |
| `Nexus AI/src/lib/api.ts` | 🆕 `apiFetch()` 超时封装 |
| `Nexus AI/src/App.tsx` | 🔧 改用 apiFetch，修复错误处理 |
| `Nexus AI/src/components/Login.tsx` | 🔧 改用 apiFetch，保留错误消息 |
| `Nexus AI/src/components/MainPage.tsx` | 🔧 空 catch 加日志 |
| `Nexus AI/src/components/Sidebar.tsx` | 🔧 3 处空 catch 加日志 |
| `Nexus AI/src/components/AdminPage.tsx` | 🔧 2 处空 catch 加日志 |
| `Nexus AI/src/components/TaskHistory.tsx` | 🔧 2 处空 catch 加日志 |
| `Nexus AI/src/components/AssetLibrary.tsx` | 🔧 2 处空 catch 加日志 |
| `Nexus AI/src/components/SettingsPage.tsx` | 🔧 空 catch 加日志 |
| `Nexus AI/vite.config.ts` | 🔧 PWA 配置修复 |
| `Nexus AI/tsconfig.app.json` | 🔧 TypeScript 严格模式 |
| `start.sh` | 🔧 路径使用绝对引用，Tunnel 等待检测 |

### 依赖变更

```text
+ bcrypt>=4.2.0      # 替代 SHA-256，安全的密码哈希
```

---

## 2026-06-02 — v2.6 PWA + 通知 + 引导 + 结构整理

### 新增功能

| 功能 | 说明 |
|------|------|
| **PWA 支持** | `vite-plugin-pwa` 集成，Service Worker 离线缓存，manifest.webmanifest，手机可添加到主屏幕 |
| **通知系统** | 后端 `notifications` 表 + API，feature request 审核时自动创建通知，前端铃铛图标 + 红点 badge + 30s 轮询 + 下拉面板 |
| **端到端引导导览** | 5 步 GuidedTour（欢迎→描述→生成→安全→团队），替代旧静态 checklist，支持上一步/跳过 |
| **项目结构整理** | 根目录从 14 个文件精简到 6 个，deploy/、docs/、assets/ 分类管理 |

### UX 改进

| 改进 | 说明 |
|------|------|
| **侧边栏角色过滤** | `member` 角色只看到 Team/AI Tools/Assets/History，减少非技术用户噪音 |
| **通知实时反馈** | 提交 feature request 后，审核结果通过铃铛红点即时通知，不再需要手动刷新 |
| **引导体验升级** | 从静态清单改为步骤式导览，每步有 emoji + 说明 + 高亮提示 |

### PWA 配置

| 配置项 | 值 |
|--------|-----|
| short_name | Truffle |
| theme_color | #0D1117 |
| display | standalone (全屏沉浸) |
| 离线缓存 | 静态资源 (js/css/html/svg) + 通知 API NetworkFirst |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `app/db.py` | 🆕 `notifications` 表 (id, user_id, type, title, message, related_id, is_read, created_at) |
| `app/api/notifications.py` | 🆕 新建 — 通知 CRUD API (list/unread-count/mark-read/read-all) |
| `app/api/team.py` | review_request() 审核时自动创建通知给提交者 |
| `app/main.py` | 注册 notifications_router |
| `Nexus AI/package.json` | 🆕 + vite-plugin-pwa |
| `Nexus AI/vite.config.ts` | 🆕 PWA 插件配置 (manifest + SW + runtimeCaching) |
| `Nexus AI/index.html` | 🆕 manifest / theme-color / apple-mobile-web-app meta |
| `Nexus AI/public/pwa-icon.svg` | 🆕 PWA 图标 (512x512 pig logo + 星星 + 盾牌) |
| `Nexus AI/src/components/Sidebar.tsx` | 🔄 重写：通知铃铛 + 未读红点 + 下拉面板 + 角色过滤导航 |
| `Nexus AI/src/components/Dashboard.tsx` | 🆕 通知轮询 (30s) + unreadCount 传递 |
| `Nexus AI/src/components/MainPage.tsx` | 🔄 GettingStartedBanner → GuidedTour (5步导览) |
| `Nexus AI/src/lib/translations.ts` | 🆕 通知 + 导览 中英文翻译 |

### 结构整理

| 移动前 | 移动后 |
|--------|--------|
| `docker-compose.yml` | `deploy/docker-compose.yml` |
| `Dockerfile.tunnel` | `deploy/Dockerfile.tunnel` |
| `tunnel-config.yml` | `deploy/tunnel-config.yml` |
| `yizhizhu/` (根目录) | `docs/yizhizhu/` |
| `猪猪.png` (根目录) | `assets/猪猪.png` |
| README/CHANGELOG/OPS/CODE_MAP (根目录) | `docs/` 下 |

---

## 2026-06-02 — v2.5 Bug 修复 + 数据库清理 + 历史任务

### 新增功能

| 功能 | 说明 |
|------|------|
| **Task History（任务历史页面）** | 侧边栏新增"History"按钮，查看所有历史生成任务，展开可看代码和扫描报告 |
| **删除用户级联清理** | 删除用户时自动清理 generation_tasks、scan_results、review_requests、code_assets、teams、team_members、feature_requests |

### Bug 修复

| Bug | 说明 |
|-----|------|
| **Free Tier 不可用** | `.env` 中 `SERVER_DEEPSEEK_KEY` 已取消注释并填入有效 Key，无 API Key 用户可正常生成 |
| **测试数据冗余** | 清理由自动测试产生的 48 个孤立团队和 2 个 admin 测试团队，保留唯一真实团队 |

### UX 改进

| 改进 | 说明 |
|------|------|
| **引导更新** | Onboarding step2 从"Add API Key"改为"Free Tier — describe your idea"，不再跳转 Settings |
| **历史记录入口** | 侧边栏新增"History"，方便找回之前生成的代码 |

### 运维

| 操作 | 说明 |
|------|------|
| **清理遗留数据库** | `data/auth.db` 和 `data/chat_history.db` 迁移完成（sentinel 确认），已移至 `data/legacy_backup/` |
| **数据库瘦身** | teams 51→1, team_members 58→1, feature_requests 29→1 |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/.env` | 取消注释 SERVER_DEEPSEEK_KEY，填入有效 Key |
| `platform-backend/app/api/admin.py` | 删除用户新增级联清理（tasks/scans/reviews/assets/teams） |
| `Nexus AI/src/components/TaskHistory.tsx` | 🆕 新建 — 任务历史页面，支持展开查看代码和扫描报告 |
| `Nexus AI/src/components/Dashboard.tsx` | 引入 TaskHistory 组件，注册 history 路由 |
| `Nexus AI/src/components/Sidebar.tsx` | 新增 history 导航按钮 + NavIcon |
| `Nexus AI/src/lib/translations.ts` | 新增 sidebar.history 中英文翻译；更新 onboarding.step2 文案 |
| `Nexus AI/src/components/MainPage.tsx` | Onboarding step2 action 从跳转 Settings 改为聚焦输入框 |

---

## 2026-06-02 — v2.4 管理后台独立端口 + 数据浏览器

### Breaking Changes

- **管理后台移到独立端口 8002**：admin API 不再通过 `trufflekit.com` 暴露，只绑 `127.0.0.1`
- **审核管理路由变动**：`/api/v1/review/pending`、`/api/v1/review/all`、`/api/v1/review/{id}/decide` 已移至 `/api/v1/admin/reviews/*`
- **Admin 入口从主站移除**：不再显示在侧边栏，通过 `http://127.0.0.1:8002` 直接访问

### 新增功能

| 功能 | 说明 |
|------|------|
| **独立管理端口 8002** | Admin 服务只监听 `127.0.0.1`，互联网无法访问 |
| **Data Browser（数据浏览器）** | 左侧选表、右侧查看数据、支持分页，无需写 SQL |
| **自动登录** | 打开 `http://127.0.0.1:8002` 自动获取 admin JWT，跳过登录页 |
| **独立管理界面** | 8002 直接渲染 AdminPage，无侧边栏、无登录页 |
| **Admin 连接检测** | 管理后台自动检测 8002 是否运行，未启动时显示提示 |

### 安全提升

- admin API 从公网移除，只有你本机 localhost 能访问
- 外出时通过 `ssh -L 8002:127.0.0.1:8002 your-server` 隧道访问
- 审核、用户管理、数据浏览全部走独立端口

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/admin_app.py` | 🆕 新建 — 独立 FastAPI 实例，admin-only |
| `platform-backend/app/api/admin.py` | 新增审核管理、Data Browser、payment config 端点 |
| `platform-backend/app/api/review.py` | 移除 admin 端点，仅保留用户端 |
| `platform-backend/app/main.py` | 移除 admin_router 引用 |
| `Nexus AI/src/components/AdminPage.tsx` | API 调用走 8002 端口，新增 Database 标签页 |
| `start.sh` | 新增 admin server 启动，双进程管理 |

---

## 2026-06-02 — v2.3 零配置生成 + Ollama 自动检测

### 新增功能

| 功能 | 说明 |
|------|------|
| **零配置生成** | 用户无需配置任何 API Key，直接点击"生成代码"即可使用 |
| **Ollama 自动检测** | 后端自动检测本地 Ollama 是否运行，优先用本地模型 |
| **服务端共享 Key 兜底** | 没有 Ollama 时自动用服务端 DeepSeek Key（需配置） |
| **免费提示** | 未配置 Key 的用户看到"Free Tier"提示，而不是报错 |

### 自动检测流程

```
用户点击"生成代码"（未配置 API Key）
    ↓
后端检测 Ollama（localhost:11434）
    ├── 运行中 → 用 Ollama 本地生成（qwen2.5-coder:7b）
    └── 未运行 → 用 SERVER_DEEPSEEK_KEY 生成
                     ↓
             没有配置 Key → 报错提示
```

### 涉及文件

| 文件 | 变更 |
|------|------|
| `platform-backend/app/api/generate.py` | 新增 `_is_ollama_running()`, `_resolve_auto_config()`, 非流式+流式双端自动检测 |
| `Nexus AI/src/components/Dashboard.tsx` | 移除 API Key 硬检查，允许空 Key 发送 |
| `Nexus AI/src/components/MainPage.tsx` | "No API key" 改为 "Free Tier" 提示 |
| `platform-backend/.env` | 新增 `SERVER_DEEPSEEK_KEY` / `SERVER_DEFAULT_MODEL` 配置项 |
| `Nexus AI/src/components/Dashboard.tsx` | 默认落地页改为 AI Tools 页面（非团队页） |
| `Nexus AI/src/components/ReviewPage.tsx` | 自动填充 task_id，无需用户手动复制粘贴 |
| `Nexus AI/src/context/LanguageContext.tsx` | 自动检测浏览器语言，中文用户默认显示中文 |

### UX 改进

| 改进 | 说明 |
|------|------|
| **默认落地页改为 AI Tools** | 登录后直接看到粘贴扫描 + 模板 + 引导，不再落到空白团队页 |
| **"提交审核"自动带 task_id** | 生成完代码点"提交审核"→ 自动填好 Task ID，用户只需写备注 |
| **语言自动检测** | 中文浏览器用户默认显示中文，不再突然出现不匹配的语言 |

### 部署注意

- 启用共享 Key：取消注释 `platform-backend/.env` 中的 `SERVER_DEEPSEEK_KEY` 并填入 Key
- 启用 Ollama：在服务器上安装 Ollama `curl -fsSL https://ollama.com/install.sh | sh` 并拉取模型

---

## 2026-06-02 — v2.2 功能补齐 + 架构整理

### Breaking Changes

- **数据库合并**: `auth.db` 和 `chat_history.db` 已合并到 `app.db`。首次启动自动迁移遗留数据，幂等（仅执行一次）
- **日志合并**: 所有日志路径从 `/tmp/` 和 `platform-backend/` 集中到项目根目录 `logs/`
- **文档整合**: `CLAUDE.md` + `REQUIREMENTS_SUMMARY.md` 已合并进其他文档，删除了这两个文件

### 新增功能

| 功能 | 说明 |
|------|------|
| **Landing Page** (`/`) | 公开产品首页，Hero + Features + How It Works + CTA |
| **登录页** (`/login`) | 登录表单从 `/` 移到 `/login`，Landing Page 有 "← Back to Home" 链接 |
| **Admin 用户管理** | AdminPage 新增 Users 标签页：用户列表、角色切换、删除 |
| **资产团队筛选** | AssetLibrary 新增 Team 下拉筛选，传 `team_id` 到后端 |
| **Stripe 支付集成** | 支持 Stripe Checkout，审核需先支付（需配置环境变量激活） |

### 安全修复

| 事项 | 状态 |
|------|------|
| `SECRET_KEY` 配置 | ✅ 生成 64 位随机密钥，写入 `.env` |
| `CORS_ORIGINS` 配置 | ✅ 设为 `https://trufflekit.com` |
| Nginx `server_name` | ✅ 域名固定，无需修改 |

### 涉及文件

| 文件 | 变更 |
|------|------|
| `Nexus AI/src/components/LandingPage.tsx` | 🆕 新建 |
| `Nexus AI/src/App.tsx` | 路由逻辑：`/` → Landing, `/login` → Login |
| `Nexus AI/src/components/Login.tsx` | 新增 "← Back to Home" |
| `Nexus AI/src/components/AdminPage.tsx` | 🆕 Users 标签页 |
| `Nexus AI/src/components/AssetLibrary.tsx` | 🆕 Team 下拉筛选 |
| `Nexus AI/src/components/ReviewPage.tsx` | 🆕 显示价格 + 支付按钮 |
| `platform-backend/app/db.py` | auth + chat 表定义, `migrate_from_legacy()` |
| `platform-backend/app/auth/auth.py` | `_get_conn()` → 委托给 app.db |
| `platform-backend/app/api/chat_history.py` | `_get_conn()` → 委托给 app.db |
| `platform-backend/app/main.py` | 启动时调用 `migrate_from_legacy()`, 注册 payment router |
| `platform-backend/app/api/payment.py` | 🆕 Stripe Checkout + webhook |
| `platform-backend/app/api/review.py` | 支持 `pending_payment` 状态 |
| `.env` | 新增 `SECRET_KEY`, `CORS_ORIGINS`, Stripe 配置项 |
| **日志合并** | `start.sh` 6 处路径, `main.py` 默认 LOG_FILE |
| `.gitignore` | `logs/` 替代旧的 `*.log` |
| `CODE_MAP.md` | 更新 DB 章节, 新增 LandingPage/payment/AdminPage 用户管理 |
| `README.md` | 🆕 功能状态一览章节, 更新架构图/DB/路由/环境变量 |
| `OPS.md` | 更新日志/DB/测试/部署/安全章节 |

### 验证

- 后端 114/115 测试通过
- 数据库迁移幂等（已打 sentinel 标记）
- 所有 `/tmp/truffle-*.log` 路径迁移为 `logs/*.log`

## 2026-06-01 — 修复 Cloudflare Tunnel 连接问题

### 问题

`https://trufflekit.com` 返回 502/530，无法正常访问。

### 根因及修复

#### 1. Docker 容器内 IPv4/IPv6 不匹配

`socat` 只监听 IPv4 (`0.0.0.0:8000`)，但 Alpine 容器内 `localhost` 优先解析到 IPv6 (`::1`)，
`cloudflared` 连接 `localhost:8000` 走到 IPv6 导致连接失败。

**修复** (`Dockerfile.tunnel`): CMD 中先执行 `echo '127.0.0.1 localhost' > /etc/hosts`，强制 `localhost` 走 IPv4。

#### 2. host.docker.internal 指向 Windows 而非 WSL2

在 WSL2 + Docker Desktop 环境下，`host.docker.internal` 解析到 Windows 主机 IP，但后端
uvicorn 运行在 WSL2 上，socat 转发到 Windows 侧连不上。

**修复** (`Dockerfile.tunnel`): 将转发目标从 `host.docker.internal:${BACKEND_PORT}` 改为
`172.17.0.1:${BACKEND_PORT}`（Docker 网关始终指向 Docker 宿主机 = WSL2 VM）。

#### 3. start.sh 找不到 Tunnel Token

Token 仅通过手动 `docker run -e TUNNEL_TOKEN=...` 传入，未持久化，
`start.sh` 的 `get_tunnel_token()` 无法找到它。

**修复** (`start.sh` + `.env`):
- 新建 `.env` 文件存放 `TUNNEL_TOKEN`
- `start.sh` 启动时自动加载 `PROJECT_DIR/.env`

### 涉及文件

| 文件 | 变更 |
|---|---|
| `Dockerfile.tunnel` | 修复 IPv4/IPv6 解析、修复 host.docker.internal 指向 |
| `start.sh` | 新增 `.env` 自动加载逻辑 |
| `.env` | 新建，持久化 `TUNNEL_TOKEN` |

### 验证

- `https://trufflekit.com` → HTTP 200
- `./start.sh` 一键启动 → 隧道自动拉起
- `./start.sh --stop && ./start.sh` → 全流程重启正常
