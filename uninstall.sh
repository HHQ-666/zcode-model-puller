#!/usr/bin/env bash
#
# ZCode 自定义模型自动拉取增强工具 - 一键卸载与还原脚本
#

set -e

echo "========================================================"
echo "🔄 正在将 ZCode 还原至官方原版状态..."
echo "========================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/inject_tool.py" --restore

echo ""
echo "🎉 还原完成！ZCode 已恢复至官方原装状态。"
