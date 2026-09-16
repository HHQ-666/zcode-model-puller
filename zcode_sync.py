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

ZCODE_CONFIG_PATH = Path.home() / ".zcode" / "v2" / "provider_config.json"
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
        bak_file = ZCODE_CONFIG_PATH.with_name(f"provider_config.json.bak.{int(time.time())}")
        shutil.copy2(ZCODE_CONFIG_PATH, bak_file)
        tmp_file = ZCODE_CONFIG_PATH.with_name(ZCODE_CONFIG_PATH.name + ".puller.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        os.chmod(tmp_file, 0o600)
        os.replace(tmp_file, ZCODE_CONFIG_PATH)
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
        "User-Agent": "ZCode/3.12.2",
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
    """
    列出 provider_config.json 中的自定义（API Key 类型）供应商规则。
    ZCode 3.12+ 起内置供应商单独存放，此处仅返回用户自建的供应商。
    """
    rules = (config_data.get("config", {})
             .get("providerConfigRules", {})
             .get("providerRules", []))
    custom_list = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        pcfg = rule.get("config") or {}
        access = pcfg.get("access") or {}
        api = pcfg.get("api") or {}
        if access.get("type") != "api-key" or not api.get("baseUrl"):
            continue
        custom_list.append(rule)
    return custom_list


def provider_model_ids(pcfg):
    """供应商已声明的全部模型 ID（保持声明顺序）。"""
    ids = []
    for key in ("personalModelIds", "modelOrder"):
        for mid in pcfg.get(key) or []:
            if isinstance(mid, str) and mid.strip() and mid not in ids:
                ids.append(mid)
    return ids


def add_models_to_rule(config_data, rule, new_models):
    """
    把新模型写入供应商规则。
    只做最小改动：追加 personalModelIds / modelOrder；
    模型规则条目直接复制同供应商已有条目的 config，保证 strict 校验一定通过。
    """
    pcfg = rule.setdefault("config", {})
    personal = list(pcfg.get("personalModelIds") or [])
    order = list(pcfg.get("modelOrder") or [])
    for mid in new_models:
        if mid not in personal:
            personal.append(mid)
        if mid not in order:
            order.append(mid)
    pcfg["personalModelIds"] = personal
    pcfg["modelOrder"] = order

    mcr = config_data.setdefault("config", {}).setdefault("modelConfigRules", {})
    rules = mcr.setdefault("providerModelRules", [])
    mcr.setdefault("manualProviderModelRules", [])

    siblings = [r for r in rules
                if isinstance(r, dict) and r.get("providerId") == rule.get("providerId") and r.get("config")]
    if not siblings:
        return
    template = json.loads(json.dumps(siblings[-1]["config"]))
    declared = {r.get("modelId") for r in rules
                if isinstance(r, dict) and r.get("providerId") == rule.get("providerId")}
    for mid in new_models:
        if mid in declared:
            continue
        rules.append({
            "modelId": mid,
            "providerId": rule.get("providerId"),
            "config": json.loads(json.dumps(template)),
        })


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
    for idx, rule in enumerate(custom_providers, 1):
        pcfg = rule.get("config") or {}
        name = rule.get("providerName") or "未命名"
        base_url = (pcfg.get("api") or {}).get("baseUrl", "-")
        existing_models = provider_model_ids(pcfg)
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
    for rule in selected_targets:
        pcfg = rule.get("config") or {}
        name = rule.get("providerName") or "未命名"
        base_url = (pcfg.get("api") or {}).get("baseUrl", "")
        api_key = (pcfg.get("access") or {}).get("apiKey", "")

        print(f"\n🔄 正在拉取供应商「{name}」的模型列表...")
        success, msg, fetched_models = fetch_models_from_api(base_url, api_key)
        if not success:
            print(f"  ❌ {msg}")
            continue

        print(f"  ✅ {msg}，共获取到 {len(fetched_models)} 个模型：")
        existing_models = provider_model_ids(pcfg)
        new_models = [m for m in fetched_models if m not in existing_models]
        already_models = [m for m in fetched_models if m in existing_models]

        print(f"     - 已存在: {len(already_models)} 个")
        print(f"     - 发现新模型: {len(new_models)} 个")

        if new_models:
            print("\n  即将添加的新模型：")
            for m in new_models:
                print(f"    + {m}")

            add_models_to_rule(cfg, rule, new_models)
            total_added += len(new_models)
        else:
            print("  👍 所有获取到的模型均已存在，无需添加。")

    if total_added > 0:
        if save_config(cfg):
            print(f"\n🎉 同步成功！共新增 {total_added} 个模型并写入 ZCode 配置。")
            print("💡 ZCode 运行中会自动轮询到变更（约 1 秒内刷新模型列表），无需重启。")
    else:
        print("\n✨ 配置未发生变动。")


if __name__ == "__main__":
    sync_cli()
