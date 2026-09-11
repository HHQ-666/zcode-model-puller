#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 自定义供应商模型自动拉取与同步工具
- 支持一键拉取指定/所有自定义供应商的模型列表并同步到 ZCode 配置中
- 支持一键注入到 ZCode 软件界面中，在设置页面新增「⚡️ 自动拉取模型」按钮
- 支持一键还原 ZCode 软件至原版
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.error
from pathlib import Path

ZCODE_CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
ZCODE_APP_PATH = Path("/Applications/ZCode.app")
ASAR_PATH = ZCODE_APP_PATH / "Contents" / "Resources" / "app.asar"
ASAR_BAK_PATH = ZCODE_APP_PATH / "Contents" / "Resources" / "app.asar.original.bak"


def load_config():
    if not ZCODE_CONFIG_PATH.exists():
        print(f"❌ 找不到 ZCode 配置文件: {ZCODE_CONFIG_PATH}")
        return None
    try:
        with open(ZCODE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None


def save_config(config_data):
    try:
        # 备份一份
        bak_file = ZCODE_CONFIG_PATH.with_name(f"config.json.bak.{int(time.time())}")
        shutil.copy2(ZCODE_CONFIG_PATH, bak_file)
        with open(ZCODE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False


def fetch_models_from_api(base_url: str, api_key: str = "", timeout: int = 10):
    """
    根据 Base URL 和 API Key 自动请求供应商的 /models 接口
    自动适配 OpenAI 兼容、Anthropic、OneAPI、NewAPI、Ollama 等
    """
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        return False, "Base URL 为空", []

    candidates = []
    if base_url.endswith("/v1"):
        candidates.append(f"{base_url}/models")
        candidates.append(f"{base_url[:-3]}/models")
    else:
        candidates.append(f"{base_url}/v1/models")
        candidates.append(f"{base_url}/models")

    if "/api" in base_url and not base_url.endswith("/models"):
        candidates.append(f"{base_url}/v1/models")

    headers = {
        "User-Agent": "ZCode/3.11.2",
        "Accept": "application/json",
    }
    if api_key:
        api_key = api_key.strip()
        headers["Authorization"] = f"Bearer {api_key}"
        headers["x-api-key"] = api_key

    last_error = ""
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    raw_data = resp.read().decode("utf-8")
                    data = json.loads(raw_data)
                    
                    models_raw = []
                    if isinstance(data, list):
                        models_raw = data
                    elif isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], list):
                            models_raw = data["data"]
                        elif "models" in data and isinstance(data["models"], list):
                            models_raw = data["models"]

                    model_ids = []
                    for item in models_raw:
                        mid = ""
                        if isinstance(item, str):
                            mid = item.strip()
                        elif isinstance(item, dict):
                            mid = (item.get("id") or item.get("name") or "").strip()
                        if mid and mid not in model_ids:
                            model_ids.append(mid)

                    if model_ids:
                        model_ids.sort()
                        return True, f"成功从 {url} 获取", model_ids
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            last_error = str(e)

    return False, f"拉取失败: {last_error or '未能解析到有效模型列表'}", []


def list_providers(config_data):
    providers = config_data.get("provider", {})
    custom_list = []
    for pid, pdata in providers.items():
        # 排除官方内置的 provider（如 builtin:bigmodel, builtin:zai 等）
        if not pid.startswith("builtin:") and pdata.get("source") == "custom":
            custom_list.append((pid, pdata))
    return custom_list


def sync_cli():
    print("=" * 60)
    print("🤖 ZCode 自定义模型供应商 - 模型自动同步工具")
    print("=" * 60)

    cfg = load_config()
    if not cfg:
        return

    custom_providers = list_providers(cfg)
    if not custom_providers:
        print("💡 暂未在 ZCode 中找到任何自定义供应商，请先在 ZCode 软件中添加供应商。")
        return

    print(f"\n已找到 {len(custom_providers)} 个自定义供应商：")
    for idx, (pid, pdata) in enumerate(custom_providers, 1):
        name = pdata.get("name", "未命名")
        base_url = pdata.get("options", {}).get("baseURL", "-")
        existing_models = list(pdata.get("models", {}).keys())
        print(f"  [{idx}] {name}")
        print(f"      Base URL: {base_url}")
        print(f"      已有模型数: {len(existing_models)}")

    print("\n请选择要同步的供应商编号 (输入 a 同步全部, 输入 q 退出): ", end="")
    choice = input().strip()
    if choice.lower() == "q":
        return

    selected_targets = []
    if choice.lower() == "a":
        selected_targets = custom_providers
    elif choice.isdigit() and 1 <= int(choice) <= len(custom_providers):
        selected_targets = [custom_providers[int(choice) - 1]]
    else:
        print("❌ 输入无效")
        return

    total_added = 0
    for pid, pdata in selected_targets:
        name = pdata.get("name", "未命名")
        opts = pdata.get("options", {})
        base_url = opts.get("baseURL", "")
        api_key = opts.get("apiKey", "")

        print(f"\n🔄 正在拉取供应商「{name}」的模型列表...")
        success, msg, fetched_models = fetch_models_from_api(base_url, api_key)
        if not success:
            print(f"  ❌ {msg}")
            continue

        print(f"  ✅ {msg}，共获取到 {len(fetched_models)} 个模型：")
        existing_models = pdata.get("models", {})
        new_models = [m for m in fetched_models if m not in existing_models]
        already_models = [m for m in fetched_models if m in existing_models]

        print(f"     - 已存在: {len(already_models)} 个")
        print(f"     - 发现新模型: {len(new_models)} 个")

        if new_models:
            print("\n  即将添加的新模型：")
            for m in new_models:
                print(f"    + {m}")

            for m in new_models:
                existing_models[m] = {
                    "limit": {
                        "context": 1000000,
                        "output": 128000
                    },
                    "modalities": {
                        "input": ["text", "image", "video"],
                        "output": ["text"]
                    },
                    "zcode": {
                        "modalitiesConfigured": True,
                        "modified": True
                    }
                }
            pdata["models"] = existing_models
            total_added += len(new_models)
        else:
            print("  👍 所有获取到的模型均已存在，无需添加。")

    if total_added > 0:
        if save_config(cfg):
            print(f"\n🎉 同步成功！共新增 {total_added} 个模型并写入 ZCode 配置。")
            print("💡 如果 ZCode 正在运行，请重启或切换一下页面即可刷新模型列表！")
    else:
        print("\n✨ 配置未发生变动。")


if __name__ == "__main__":
    sync_cli()
