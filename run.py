#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 模型自动获取与界面注入综合工具
"""

import sys
import os
from pathlib import Path
from zcode_sync import sync_cli, fetch_models_from_api
from inject_tool import install_injection, restore_asar


def test_url_key_interactive():
    print("\n--- 🧪 自定义 URL / API Key 连通测试 ---")
    url = input("请输入 Base URL (例如 https://line.kukewang.com/v1): ").strip()
    if not url:
        print("❌ URL 不能为空")
        return
    key = input("请输入 API Key (没有可直接回车): ").strip()

    print("\n🔄 正在获取模型列表...")
    success, msg, models = fetch_models_from_api(url, key)
    if success:
        print(f"✅ {msg}")
        print(f"共获取到 {len(models)} 个可用模型：")
        for idx, m in enumerate(models, 1):
            print(f"  [{idx:02d}] {m}")
    else:
        print(f"❌ {msg}")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ["--inject", "--install", "-i"]:
            install_injection()
            return
        elif arg in ["--restore", "--uninstall", "-r"]:
            restore_asar()
            return
        elif arg in ["--sync", "-s"]:
            sync_cli()
            return
        elif arg in ["--test", "-t"]:
            test_url_key_interactive()
            return

    while True:
        print("\n" + "=" * 50)
        print("  🛠️  ZCode 自定义供应商模型增强工具箱")
        print("=" * 50)
        print("  [1] 一键将「⚡️ 自动拉取模型」按钮注入到 ZCode 软件界面")
        print("  [2] 命令行交互式同步：自动读取 ZCode 供应商并更新模型")
        print("  [3] 独立测试：输入任意 URL 和 API Key 获取模型列表")
        print("  [4] 还原 ZCode：一键恢复原版（卸载注入并恢复官方 ASAR）")
        print("  [0] 退出")
        print("=" * 50)
        choice = input("请选择功能编号 [0-4]: ").strip()

        if choice == "1":
            install_injection()
        elif choice == "2":
            sync_cli()
        elif choice == "3":
            test_url_key_interactive()
        elif choice == "4":
            restore_asar()
        elif choice in ["0", "q", "exit"]:
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()
