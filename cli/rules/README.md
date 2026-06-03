# TruffleKit 规则库

> 所有扫描规则完全开源，可审计，可验证。

每条规则包含：
- **检测逻辑** — 匹配什么模式，为什么
- **行号 + 代码片段** — 你可以亲自验证
- **修复建议** — 具体怎么修
- **参考来源** — OWASP / CVE / 官方文档

---

## 严重等级说明

| 等级 | 含义 | 行动 |
|---|---|---|
| 🔴 Critical | 必须修复才能上线 | 阻止上线 |
| 🟠 High | 强烈建议上线前修复 | 建议修复 |
| 🟡 Medium | 建议修复 | 择机处理 |
| 🔵 Low | 项目健康度建议 | 不紧急 |
| ⚪ Info | 信息提示 | 看看就好 |

---

## 全部规则

### 密钥泄露

| 规则 | 等级 | 说明 |
|---|---|---|
| [SEC-001](SEC-001.md) | 🔴 Critical | API Key / Secret 硬编码在源码中 |
| [SEC-002](SEC-002.md) | 🟠 High | .env 文件未被 .gitignore 保护 |
| [SEC-003](SEC-003.md) | 🟠 High | Git 历史中曾提交过敏感文件 |
| [SEC-004](SEC-004.md) | 🟡 Medium | .gitignore 缺少关键规则 |
| [SEC-005](SEC-005.md) | 🔴 Critical | SSL 私钥文件在项目目录中 |

### 代码质量

| 规则 | 等级 | 说明 |
|---|---|---|
| [SEC-006](SEC-006.md) | 🟡 Medium | 生产代码残留调试输出 |
| [SEC-007](SEC-007.md) | 🔵 Low | TODO/FIXME 累计 |
| [SEC-015](SEC-015.md) | 🟡 Medium | 空的 catch/except 块 |

### 安全配置

| 规则 | 等级 | 说明 |
|---|---|---|
| [SEC-020](SEC-020.md) | 🔴 Critical | 默认管理员密码 |
| [SEC-021](SEC-021.md) | 🟡 Medium | CORS 配置过于宽松 |
| [SEC-022](SEC-022.md) | 🟠 High | DEBUG 模式未关闭 |

### 项目健康

| 规则 | 等级 | 说明 |
|---|---|---|
| [SEC-008](SEC-008.md) | 🟡 Medium | 敏感文件权限过于宽松 |
| [SEC-009](SEC-009.md) | 🟡 Medium | 硬编码本地绝对路径 |
| [SEC-010](SEC-010.md) | 🟠 High | 数据库文件可被下载 |
| [SEC-011](SEC-011.md) | 🔵 Low | 项目中存在大文件 |
| [SEC-016](SEC-016.md) | 🔵 Low | 缺少 README |
| [SEC-017](SEC-017.md) | 🔵 Low | 缺少 LICENSE |
| [SEC-018](SEC-018.md) | ⚪ Info | 缺少 CI/CD |

### Docker

| 规则 | 等级 | 说明 |
|---|---|---|
| [SEC-012](SEC-012.md) | 🟡 Medium | Docker 端口暴露到公网 |
| [SEC-013](SEC-013.md) | 🔵 Low | 使用 latest 标签 |

### 依赖

| 规则 | 等级 | 说明 |
|---|---|---|
| [SEC-014](SEC-014.md) | 🟡 Medium | 依赖未固定版本号 |
| [SEC-019](SEC-019.md) | 🔵 Low | node_modules/vendor 被提交 |

---

## 如何贡献规则

1. 在 `cli/rules.py` 中用 `@register` 装饰器添加新规则
2. 在 `cli/rules/` 下添加对应的文档文件
3. 提 PR 或直接提交

---

## 参考来源

所有规则的参考来源遵循：
- OWASP Top 10 (2021)
- CVE 数据库
- 各语言/框架官方安全最佳实践
