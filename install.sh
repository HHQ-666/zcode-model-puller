#!/usr/bin/env bash
#
# ZCode 自定义模型自动拉取增强工具 - 一键安装脚本
#
# 用法：
#   ./install.sh             安装注入 + 启用更新守护（ZCode 更新后自动重装）
#   ./install.sh --no-watch  仅安装注入，不启用更新守护
#

set -e

echo "========================================================"
echo "⚡️ 正在为 ZCode 安装「自动拉取模型」增强插件..."
echo "========================================================"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未检测到 python3，请先安装 Python 3"
    exit 1
fi

# 检查 Node / npx
if ! command -v npx &> /dev/null; then
    echo "❌ 错误: 未检测到 npx (Node.js)，请先安装 Node.js"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 执行注入
python3 "${SCRIPT_DIR}/inject_tool.py"

if [[ "${1:-}" == "--no-watch" ]]; then
    echo ""
    echo "🎉 安装完成（未启用更新守护）！请重启 ZCode（Command + Q 退出后再启动）即可体验！"
    exit 0
fi

echo ""
echo "========================================================"
echo "⚡️ 正在启用「ZCode 更新守护」（更新后自动重新注入）..."
echo "========================================================"

python3 "${SCRIPT_DIR}/watch_agent.py" install

echo ""
echo "🎉 安装完成！请重启 ZCode（Command + Q 退出后再启动）即可体验！"