# 发布到 PyPI

让全世界都能 `pip install trufflekit`。

---

## 前置准备

```bash
# 1. 安装打包工具
pip install build twine

# 2. 注册 PyPI 账号
#    打开 https://pypi.org/account/register/
#    用你的邮箱注册

# 3. 创建一个 API Token
#    https://pypi.org/manage/account/token/
#    权限选 "整个账号"，复制 token 保存好
```

---

## 构建

在项目根目录（有 `pyproject.toml` 的地方）运行：

```bash
python -m build
```

这会在 `dist/` 下生成 `.tar.gz` 源码包和 `.whl` 轮子包。

---

## 发布

```bash
# 首次发布（会提示输入用户名和 token）
python -m twine upload dist/*

# 以后更新版本时，先改 pyproject.toml 里的 version，再重复构建+上传
```

输入用户名时填 `__token__`，密码时填刚才复制的 API Token。

---

## 版本更新流程

每次发布新版本：

1. 改 `cli/__init__.py` 里的 `__version__`
2. 改 `pyproject.toml` 里的 `version`
3. 更新 `CHANGELOG.md`（如果有）
4. 重新构建 + 上传

```bash
python -m build
python -m twine upload dist/*
```

---

## 验证安装

```bash
# 装一遍看看能不能用
pip install trufflekit
truffle --version
truffle scan /path/to/some/project
```

---

## 附：发布到 TestPyPI（可选，先练习用）

```bash
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ trufflekit
```
