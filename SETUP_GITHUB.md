# 发布到 GitHub

## 第一步：在 GitHub 上创建仓库

1. 打开 https://github.com/new
2. Repository name 填 `auditize`
3. Description 填 `Auditize CLI — AI 项目确定性安全审查工具`
4. 选 Public
5. 不要勾选任何初始化选项（我们已经有了本地仓库）
6. 点 "Create repository"

## 第二步：推送本地代码

复制 GitHub 给你的命令（在刚创建的仓库页面上有），大概是：

```bash
git remote add origin https://github.com/你的用户名/auditize.git
git branch -M main
git push -u origin main
```

如果用 SSH（需要先配置 SSH key）：
```bash
git remote add origin git@github.com:你的用户名/auditize.git
git push -u origin main
```

## 第三步：配置 GitHub Pages（可选）

在仓库 Settings → Pages 中，选 main 分支的 `/docs` 目录或 root，
可以把 `cli/README.md` 渲染成项目首页。

## 第四步：发布到 PyPI

```bash
# 1. 注册 PyPI 账号: https://pypi.org/account/register/
# 2. 创建 API Token: https://pypi.org/manage/account/token/
# 3. 复制 .pypirc.example 为 ~/.pypirc 并填写 token
cp cli/.pypirc.example ~/.pypirc
# 编辑 ~/.pypirc，把 password 换成你的 API Token

# 4. 上传
python3 -m twine upload dist/*

# 5. 验证安装
pip install auditize
auditize --version
```

搞定之后，你的 CLI 就是全世界可安装的了：
```bash
pip install auditize
auditize scan ./my-project --plan
```
