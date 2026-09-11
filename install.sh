#!/usr/bin/env bash
#
# ZCode 自定义模型自动拉取增强工具 - 一键安装脚本
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

echo ""
echo "🎉 安装完成！请重启 ZCode（Command + Q 退出后再启动）即可体验！"
