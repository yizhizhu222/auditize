#!/usr/bin/env bash
# ────────────────────────────────────────────────────────
# Auditize CLI 一键发布脚本
# ────────────────────────────────────────────────────────
# 用法：
#   1. 注册 PyPI:   https://pypi.org/account/register/
#   2. 创建 Token:  https://pypi.org/manage/account/token/
#   3. 运行:
#      export PYPI_TOKEN="pypi-你的token"
#      bash scripts/release.sh
# ────────────────────────────────────────────────────────

set -e

VERSION=$(python3 -c "from cli import __version__; print(__version__)")
echo "📦  Auditize CLI v$VERSION 发布工具"
echo ""

# 1. 检查 Token
if [ -z "$PYPI_TOKEN" ]; then
  echo "❌ 请设置 PYPI_TOKEN 环境变量"
  echo "   export PYPI_TOKEN=\"pypi-你的token\""
  exit 1
fi

# 2. 清理旧构建
echo "🧹  清理旧构建..."
rm -rf dist/ *.egg-info/

# 3. 重新构建
echo "🔨  构建包..."
python3 -m build --no-isolation 2>&1 | tail -3

# 4. 检查
echo "🔍  检查包..."
python3 -m twine check dist/* 2>&1 | grep -E "PASSED|FAILED"

# 5. 上传
echo "🚀  上传到 PyPI..."
TWINE_USERNAME="__token__" TWINE_PASSWORD="$PYPI_TOKEN" \
  python3 -m twine upload --repository pypi dist/* --non-interactive 2>&1 | grep -E "Uploading|ERROR|SUCCESS|View"

# 6. 验证
echo "✅  验证安装..."
pip install --no-cache-dir auditize-cli 2>&1 | tail -3
auditize --version

echo ""
echo "🎉  发布完成！"
echo "   pip install auditize-cli"
echo "   auditize scan ."
