# Truffle — 运维手册 (Operations Manual)

> 本文档覆盖日常运维、故障排除、数据库维护、部署更新等操作。
> 更新时间：2026-06-02 (v2.14)

---

## 目录

- [服务管理](#服务管理)
- [日志系统](#日志系统)
- [数据库维护](#数据库维护)
- [部署更新](#部署更新)
- [监控](#监控)
- [备份与恢复](#备份与恢复)
- [缓存处理](#缓存处理)
- [测试运行指南](#测试运行指南)
- [常见故障排除](#常见故障排除)
- [安全注意事项](#安全注意事项)

---

## 服务管理

### 一键启动/停止/状态

```bash
# 启动前后端（开发模式）
./start.sh

# 先构建前端再启动
./start.sh --build

# 仅启动开发服务器（不自动构建 dist/）
./start.sh --dev

# 停止所有服务
./start.sh --stop

# 查看服务状态
./start.sh --status
```

### 手动启动后端（生产端口 8001）

```bash
cd platform-backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

> ⚠️ 生产环境必须使用 **8001** 端口，Cloudflare 隧道配置指向 `localhost:8001`

### 手动启动管理后台（独立端口 8002）

```bash
cd platform-backend
source .venv/bin/activate
uvicorn app.admin_app:app --host 127.0.0.1 --port 8002
```

> ⚠️ 管理后台只监听 127.0.0.1，不暴露到公网。
> 外出管理时使用 SSH 隧道：`ssh -L 8002:127.0.0.1:8002 your-server`

### 手动启动前端

```bash
cd "Nexus AI"
npx vite --host 0.0.0.0 --port 5173
```

### 前端构建

```bash
cd "Nexus AI"
npx vite build          # 构建到 dist/
npx vite build --watch  # 增量构建（源码修改自动重建）
```

### 快速更新流程（代码修改后）

```bash
# 1. 构建前端
cd "Nexus AI"
npx vite build

# 2. 复制到后端
rm -rf ../platform-backend/app/dist && cp -r dist ../platform-backend/app/dist

# 3. 重启后端
cd ../platform-backend
pkill -f "uvicorn app.main:app" && sleep 1
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &
```

---

## 日志系统

### 日志文件位置

所有日志统一存放在项目根目录 `logs/` 下：

| 日志 | 路径 | 说明 |
|------|------|------|
| 后端应用日志 | `logs/backend-app.log` | Python 应用运行时日志（FastAPI） |
| 后端启动日志 | `logs/backend-uvicorn.log` | uvicorn 进程 stdout/stderr |
| 前端开发日志 | `logs/frontend-dev.log` | Vite 开发服务器日志 |
| 前端构建日志 | `logs/frontend-build.log` | vite build --watch 增量构建日志 |
| 隧道日志 | `logs/tunnel.log` | Cloudflare Tunnel 日志 |
| Docker 构建日志 | `logs/docker-build.log` | Docker 镜像构建日志 |
| 临时后端日志 | `/tmp/backend.log` | 后台 daemon 启动日志（nohup 输出） |

### 常用日志命令

```bash
# 查看实时日志
tail -f logs/backend-app.log

# 查看最近 N 行
tail -100 logs/backend-app.log

# 搜索错误
grep -i "error\|exception\|traceback" logs/backend-app.log

# 按日期搜索
grep "2026-06-02" logs/backend-app.log

# 搜索特定用户请求
grep "user_id=1" logs/backend-app.log

# 查看后端 nohup 日志（启动信息）
tail -20 /tmp/backend.log
```

### 日志级别

在 `platform-backend/.env` 中配置：

```env
LOG_LEVEL=INFO     # 默认，生产环境建议
LOG_LEVEL=DEBUG    # 开发调试，输出更详细
LOG_LEVEL=WARNING  # 仅警告和错误
```

### 日志轮转

后端已内置 `RotatingFileHandler`（10MB × 5 份轮转），无需额外配置。
如需系统级保留，可配合 `logrotate`：

```bash
# /etc/logrotate.d/truffle
/path/to/truffle/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

---

## 数据库维护

### 数据库文件

项目使用 **单个 SQLite 数据库** `app.db`，位于 `platform-backend/data/`。

| 数据库 | 用途 | 关键表 |
|--------|------|--------|
| `app.db` | 全部业务数据 | users, sessions, settings, generation_tasks, scan_results, code_assets, review_requests, teams, team_members, feature_requests, notifications, verification_codes, login_attempts |

> **v2.2-2.5**：auth.db + chat_history.db 已合并到 app.db，遗留文件已清理。

### 备份

```bash
# 一键备份数据库
mkdir -p backups/$(date +%Y-%m-%d)
sqlite3 platform-backend/data/app.db ".backup 'backups/$(date +%Y-%m-%d)/app.db'"
echo "Backed up to backups/$(date +%Y-%m-%d)/"

# 或直接复制（需停止服务）
cp platform-backend/data/app.db backups/$(date +%Y-%m-%d)/
```

### 恢复

```bash
# 停止服务 → 恢复数据库 → 重启
./start.sh --stop
cp backups/2026-06-01/app.db platform-backend/data/app.db
./start.sh
```

### 查看数据库内容

```bash
# 查看所有用户
sqlite3 platform-backend/data/app.db "SELECT id, username, role, created_at FROM users;"

# 查看团队列表
sqlite3 platform-backend/data/app.db "SELECT id, name, created_by, created_at FROM teams;"

# 查看团队成员
sqlite3 platform-backend/data/app.db "SELECT * FROM team_members;"

# 查看需求列表
sqlite3 platform-backend/data/app.db "SELECT id, title, status, user_id, team_id FROM feature_requests ORDER BY created_at DESC;"

# 查看代码资产
sqlite3 platform-backend/data/app.db "SELECT id, title, language, user_id, team_id FROM code_assets ORDER BY created_at DESC;"

# 查看生成任务
sqlite3 platform-backend/data/app.db "SELECT id, idea_text, language, status, created_at FROM generation_tasks ORDER BY created_at DESC LIMIT 10;"

# 查看登录尝试
sqlite3 platform-backend/data/app.db "SELECT username, success, attempted_at FROM login_attempts ORDER BY attempted_at DESC LIMIT 10;"
```

### 重置数据库（开发用）

```bash
# 停止服务
./start.sh --stop

# 删除数据库文件（服务重启时会自动重建）
rm platform-backend/data/app.db

# 重启服务（自动创建表 + admin 用户）
./start.sh
```

> ⚠️ 重置会删除所有数据，包括用户、团队、需求、资产等。

---

## 部署更新

### 从 Git 更新

```bash
# 拉取最新代码
git pull origin main

# 安装新依赖（后端）
cd platform-backend
source .venv/bin/activate
pip install -r requirements.txt --no-cache-dir

# 安装新依赖（前端）
cd "Nexus AI"
npm install

# 构建前端（生产环境）
npm run build

# 复制到后端
rm -rf ../platform-backend/app/dist && cp -r dist ../platform-backend/app/dist

# 重启后端
pkill -f "uvicorn app.main:app" && sleep 1
cd ../platform-backend && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &
```

### 数据库迁移

项目使用 SQLite，通过 `ALTER TABLE ... ADD COLUMN` 做渐进式迁移。
迁移代码在 `app/db.py` 的 `init_app_db()` 中。

```python
# 示例：app/db.py 中的渐进式迁移
try:
    conn.execute("ALTER TABLE code_assets ADD COLUMN team_id TEXT")
except sqlite3.OperationalError:
    pass  # 列已存在
```

### Production 部署步骤

```bash
# 1. 构建前端
cd "Nexus AI" && npm ci && npm run build

# 2. 安装后端依赖
cd ../platform-backend && source .venv/bin/activate && pip install -r requirements.txt

# 3. 修改 .env 配置
#    SECRET_KEY、CORS_ORIGINS、DEBUG=false
#    platform-backend/.env 中 SERVER_DEEPSEEK_KEY 等

# 4. 配置 Nginx 反向代理（参考 deploy/nginx.conf）
#    注意：nginx 代理指向 localhost:8001

# 5. 启动后端
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 首次部署新服务器

1. 安装 Python 3.10+, Node.js 18+, Nginx
2. `git clone` 项目
3. 运行 `deploy/setup.sh`
4. 配置 `platform-backend/.env`
5. 配置 Nginx + SSL（参考 `deploy/nginx.conf`）

---

## 监控

### 健康检查端点

```bash
# 后端健康检查（无需认证）
curl http://localhost:8001/api/v1/health

# 返回示例
{"status": "ok", "service": "nexus-platform", "version": "2.0.0"}
```

### 系统状态

```bash
# 系统资源状态（CPU、内存）
curl http://localhost:8001/api/v1/system/status
```

### 版本信息

```bash
curl http://localhost:8001/api/v1/version
```

### API 文档

```bash
# Swagger UI（开发时访问）
open http://localhost:8001/docs

# ReDoc
open http://localhost:8001/redoc
```

### 数据库大小监控

```bash
# 查看数据库文件大小
ls -lh platform-backend/data/app.db

# 清理 WAL 文件（SQLite 预写日志）
sqlite3 platform-backend/data/app.db "PRAGMA wal_checkpoint;"
```

### 定时备份 (cron)

```bash
# 每天凌晨 3 点备份数据库
crontab -e
# 添加：
0 3 * * * cd /path/to/truffle && mkdir -p backups/$(date +\%Y-\%m-\%d) && cp platform-backend/data/*.db backups/$(date +\%Y-\%m-\%d)/
```

### 服务进程检查

```bash
# 检查后端是否运行
ps aux | grep -E "uvicorn.*app.main" | grep -v grep

# 检查 Cloudflare 隧道
ps aux | grep cloudflared | grep -v grep

# 检查 admin 后台
ps aux | grep admin_app | grep -v grep

# 检查端口是否监听
lsof -i:8001 -i:8002
```

---

## 缓存处理

### 问题现象

部署新版本后，用户浏览器仍显示旧内容。每次刷新都回到未更新状态。

### 三层缓存架构

```
用户浏览器 ← PWA Service Worker ← CDN (Cloudflare) ← 源服务器 (uvicorn)
    ↑                    ↑                    ↑
  浏览器缓存           SW 预缓存            CDN 边缘节点缓存
```

### 排查方法

```bash
# 1. 检查后端返回的缓存头
curl -sI http://localhost:8001/ | grep -i "cache"

# 期望输出（生产环境）
# cache-control: no-cache, no-store, must-revalidate, private, max-age=0
# cdn-cache-control: no-cache
# pragma: no-cache
# expires: 0

# 2. 对比 Cloudflare 响应（从公网访问）
curl -sI https://trufflekit.com | grep -i "cache\|cf-cache"
```

### 用户侧解决

```bash
# 强刷（跳过缓存）
Windows/Linux: Ctrl + Shift + R
Mac:           Cmd + Shift + R

# 或打开开发者工具 → Application → Service Workers → Unregister
# 然后刷新页面
```

### 后端已实施的缓存策略

| 资源类型 | 缓存策略 |
|---------|---------|
| `index.html` | `no-cache, no-store, must-revalidate` — 永远不缓存 |
| `sw.js` | `no-cache, no-store, must-revalidate` — 必须最新 |
| `workbox-*.js` | `no-cache, no-store, must-revalidate` — 必须最新 |
| `assets/*.js, *.css` | PWA 预缓存，由 SW 版本号控制更新 |
| API 响应 | 默认不缓存 |

### PWA Service Worker 更新流程

```
1. 用户访问页面 → 浏览器下载新 sw.js
2. 新 SW 安装 → 直接激活 (skipWaiting)
3. 新 SW 接管所有标签页 (clientsClaim)
4. 前端监听到 activated → 自动刷新页面
5. 页面加载最新 assets (版本号已变)
```

---

## 测试运行指南

### 后端测试

```bash
cd platform-backend
source .venv/bin/activate

# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_team.py -v

# 快速运行（只看失败）
python -m pytest tests/ -v --tb=short

# 仅查看统计
python -m pytest tests/ --tb=no -q
# 输出示例: 115 passed, 1 skipped in 7.27s
```

### 测试覆盖范围

| 测试文件 | 测试数 | 覆盖模块 |
|---------|-------|---------|
| `test_auth.py` | 19 | 注册、密码登录、TOTP、JWT、OAuth、改密码、删账号 |
| `test_chat.py` | 7 | 会话 CRUD、消息读写、权限、删除 |
| `test_compile.py` | 7 | 4 语言编译运行、超时、未知语言 |
| `test_team.py` | 23 | 团队 CRUD、邀请码、角色、需求看板、审核、生成、关联 |
| `test_assets.py` | 14 | 资产保存/去重/列表/筛选/搜索/团队过滤/删除/相似检测 |
| `test_scan.py` | 14 | Python/JS/Go/C++ 4 语言安全扫描、API Key 泄露、SQL 注入、历史 |
| `test_api.py` | 31 | 专家审核、设置、导出 ZIP、Admin 用户管理、系统状态 |

**后端总计: 115 passed, 1 skipped**（Go 编译器未安装）

> 💡 所有测试使用同一 `app.db` 连接。

### 前端测试

```bash
cd "Nexus AI"

# 运行全部测试
npx vitest run

# 开发模式（watch）
npx vitest

# 运行单个文件
npx vitest run -- src/test/TeamPage.test.tsx
```

| 测试文件 | 测试数 | 覆盖模块 |
|---------|-------|---------|
| `Login.test.tsx` | 7 | 登录表单渲染、密码/TOTP 模式切换、注册、API 调用 |
| `ThemeContext.test.tsx` | 10 | 主题读写、持久化、CSS 变量、Provider 错误 |
| `ErrorBoundary.test.tsx` | 3 | 错误捕获、fallback 渲染 |
| `LanguageContext.test.tsx` | 8 | 语言切换、持久化、中英文翻译、fallback、Provider 错误 |
| `ToastContext.test.tsx` | 7 | Toast 显隐、自动消失、点击消除、类型、Provider 错误 |
| `TeamPage.test.tsx` | 8 | 无团队 UI、团队信息、需求列表、邀请码、空状态、加载态 |

**前端总计: 43 tests**

### 测试前置条件

后端测试会自动：
1. 创建独立临时 SQLite 数据库
2. 每次测试前清空所有表（含 `_LOGIN_ATTEMPTS` 内存数据）
3. 创建测试用户和管理员 JWT (`auth_headers` / `admin_headers` fixture)

前端测试通过 mock fetch 模拟 API 调用，不依赖后端运行。

---

## 备份与恢复

### 完整备份

```bash
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 数据库
cp platform-backend/data/app.db "$BACKUP_DIR/" 2>/dev/null

# 环境配置（去掉敏感信息）
cp .env "$BACKUP_DIR/.env" 2>/dev/null

# 上传文件（头像等）
cp -r platform-backend/data/avatars "$BACKUP_DIR/avatars" 2>/dev/null

# 日志
cp logs/backend-app.log "$BACKUP_DIR/" 2>/dev/null

echo "Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
```

### 从备份恢复

```bash
./start.sh --stop
cp backups/2026-06-01_143022/app.db platform-backend/data/app.db
./start.sh
```

---

## 常见故障排除

### 后端无法启动

**现象**: `./start.sh` 后后端进程退出

**排查**:

```bash
# 1. 检查日志
cat /tmp/backend.log
tail -50 platform-backend/server.log

# 2. 检查端口冲突
lsof -i :8001

# 3. 检查虚拟环境
cd platform-backend && source .venv/bin/activate && python -c "from app.main import app; print('OK')"

# 4. 检查 .env 配置
cat platform-backend/.env

# 5. 检查数据库是否损坏
sqlite3 platform-backend/data/app.db "PRAGMA integrity_check;"
```

### 前端无法启动

```bash
# 1. 检查日志
cat /tmp/truffle-frontend.log

# 2. 检查 node_modules
ls "Nexus AI/node_modules" | head -5

# 3. 重新安装依赖
cd "Nexus AI" && rm -rf node_modules && npm install

# 4. 检查 TypeScript 错误
npx tsc --noEmit
```

### 502 Bad Gateway (Cloudflare)

**现象**: trufflekit.com 返回 502，Cloudflare 报错

**排查**:

```bash
# 1. 检查后端是否在运行
ps aux | grep uvicorn | grep -v grep

# 2. 检查端口是否匹配
#    确认后端端口 == Cloudflare 隧道目标端口
#    cloudflared config: service: http://localhost:8001
lsof -i:8001

# 3. 检查本地是否可达
curl http://localhost:8001/api/v1/health

# 4. 重启隧道
pkill cloudflared
cloudflared tunnel run --token YOUR_TOKEN
```

**常见原因**: 后端重启时端口改了但 Cloudflare 隧道配置没同步。

### 部署后浏览器还是旧内容

**现象**: 构建 + 重启后，自己的浏览器看到的仍然是旧页面

**排查**:

```bash
# 1. 确认 dist 已更新
grep "LandingPage\|SafetyReport\|new_feature" platform-backend/app/dist/assets/index-*.js | head -3

# 2. 确认后端返回正确的缓存头
curl -sI http://localhost:8001/ | grep -i cache

# 3. 强刷：Ctrl+Shift+R / Cmd+Shift+R
```

**修复**: 见上方 [缓存处理](#缓存处理) 章节。

### 登录后刷新被踢回登录页

**现象**: 登录后一刷新就回到登录页

**原因**: JWT Token 过期或 localStorage 中没有正确保存 token

**修复**（v2.9）：Token 有效期已从 24 小时延长到 **7 天**。前端通过 `/api/v1/auth/verify` 验证 token 有效性。

**排查**:
```bash
# 检查 token 是否在 localStorage 中
# Chrome DevTools → Application → Local Storage → nexus-auth-token

# 检查 token 的过期时间
python3 -c "
import jwt, base64, json
token = 'YOUR_TOKEN_HERE'
payload = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
from datetime import datetime
print('Expires:', datetime.fromtimestamp(payload['exp']))
"
```

### 网站锁 IP / 浏览器缓存问题

**现象**: 同一台电脑的 Chrome 总显示旧内容，但手机/其他浏览器正常

**原因**: PWA Service Worker 和 Cloudflare 边缘节点双重缓存

**解决**:
1. Chrome 地址栏输入 `chrome://inspect/#service-workers` → Unregister
2. 或 DevTools → Application → Service Workers → Unregister
3. 然后 Ctrl+Shift+R 强刷

详见上方 [缓存处理](#缓存处理)。

### 审核回复后用户看不到报告

**现象**: 管理员审核完成后，用户在 Expert Review 只看到 verdict，没有代码和分析报告

**修复**（v2.12）：后端 `my-requests` 接口返回 `code` + `scan_report`；前端展开卡片显示 Verdict + Safety Report + Code。

### 安全扫描不检测代码质量问题

**现象**: 扫描只报安全问题，不报质量（冗余、复杂度过高等）

**修复**（v2.10）：新增 `CodeQualityAnalyzer`，覆盖 16 项检测。

### AI 生成超时 / 504

**现象**: 点击 Generate 后等待很久才出结果

**说明**: 已改为 SSE 流式输出，首 token 秒到，逐字渲染。

**排查**:
```bash
# 检查流式接口
curl -s -N --max-time 10 http://localhost:8001/api/v1/generate/stream \
  -H "Authorization: Bearer $(cat /tmp/token)" \
  -H "Content-Type: application/json" \
  -d '{"idea":"print hello","language":"python","api_key":"sk-...","model":"deepseek-chat"}'
```

### Nginx SSE 缓冲导致流式卡顿

**解决**: 在 `deploy/nginx.conf` 添加：
```nginx
proxy_buffering off;
proxy_cache off;
```

### Cloudflare Tunnel 频繁断连

**原因**: 家宽国际出口拥堵，非服务端问题。

**建议**: 开发用 `localhost:5173`，生产用国内云服务器。

### 数据库死锁 / 繁忙

```bash
sqlite3 platform-backend/data/app.db "PRAGMA journal_mode=WAL;"
./start.sh --stop && ./start.sh
```

### 磁盘空间不足

```bash
df -h
truncate -s 0 logs/backend-app.log
sqlite3 platform-backend/data/app.db "PRAGMA wal_checkpoint(TRUNCATE);"
find backups/ -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
```

---

## 安全注意事项

### 生产环境必改配置

| 配置 | 位置 | 当前值 | 说明 |
|------|------|--------|------|
| `SECRET_KEY` | `.env` | ✅ 64 位随机密钥 | JWT 签名密钥 |
| `CORS_ORIGINS` | `.env` | ✅ `https://trufflekit.com` | 跨域允许域名 |
| `DEBUG` | `.env` | `true`（开发）/ `false`（生产） | 生产务必 `false` |
| `STRIPE_SECRET_KEY` | `.env` | 注释状态 | 激活付费审核 |
| `SERVER_DEEPSEEK_KEY` | `platform-backend/.env` | ✅ 已配置 | 用户免 Key 兜底 |
| `SERVER_DEFAULT_MODEL` | `platform-backend/.env` | `deepseek-chat` | 共享 Key 默认模型 |
| **Admin 端口 8002** | `start.sh` | `127.0.0.1:8002` | 不暴露公网 |
| **后端端口 8001** | uvicorn 启动参数 | `0.0.0.0:8001` | 匹配 Cloudflare 隧道 |

### 切换域名

```bash
SITE_DOMAIN=myapp.com ./start.sh --build
```

### 生产环境建议

1. **SQLite 适合 10-50 并发**，更大规模迁移 PostgreSQL
2. **编译沙箱** — 生产用 gVisor 等容器沙箱
3. **API Key 安全** — 后端代理避免 Key 暴露给客户端
4. **HTTPS** — Cloudflare 或 Let's Encrypt
5. **速率限制** — `/api/v1/generate` 和 `/api/v1/auth/login` 限速
6. **监控告警** — UptimeRobot / Better Uptime

### 生成安全的 SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

> 最后更新: 2026-06-02 (v2.14)
>
> **版本亮点**：
> - **v2.10 代码质量检测** — 16 项质量分析：圈复杂度、死代码、空异常处理、重复代码等
> - **v2.11 Landing Page 重构** — 6 Features + 定价方案 + 合作联系 + FAQ + 滚动动画
> - **v2.12 审核报告展示** — 已完成的审核展开看 Verdict + Safety Report + 代码原文
> - **v2.13 侧边栏修复** — 所有用户可见 Expert Review 入口
> - **v2.14 缓存修复** — PWA + CDN 双层缓存处理，部署新版本自动更新
>
> **技术指标**：
> - Token 有效期: 7 天（刷新不踢）
> - 后端端口: 8001（匹配 Cloudflare 隧道）
> - 测试: 后端 115 passed, 前端 43 tests
> - 数据库: 单一 app.db，WAL 模式
> - AI: SSE 流式输出 + 服务端 DeepSeek Key 兜底
