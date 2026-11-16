# 纯函数测试：只测不依赖网络、ZCode 环境和用户目录的逻辑。
import hashlib
import json

import inject_tool
import watch_agent
import watch_reinstall
import zcode_sync


# ---------------------------------------------------------------- inject_tool

def test_collect_asar_files_flattens_nested_header():
    header = {
        "files": {
            "main.js": {"size": 10},
            "out": {"files": {"preload.js": {"size": 20}, "renderer.js": {"size": 30}}},
        }
    }
    flat = inject_tool.collect_asar_files(header)
    assert set(flat) == {"main.js", "out/preload.js", "out/renderer.js"}
    assert flat["out/preload.js"]["size"] == 20


def test_collect_asar_files_empty():
    assert inject_tool.collect_asar_files({}) == {}


def _fake_asar(tmp_path, header_dict):
    # asar 头部共 16 字节：代码从 head[8:12] 读 JSON 长度，随后从偏移 16 处读 JSON 正文，
    # 因此长度字段后还要补 4 字节才到正文。
    raw = json.dumps(header_dict).encode("utf-8")
    blob = b"\x00" * 8 + len(raw).to_bytes(4, "little") + b"\x00" * 4 + raw
    path = tmp_path / "fake.asar"
    path.write_bytes(blob)
    return path


def test_read_asar_header_roundtrip(tmp_path):
    header = {"files": {"a.js": {"size": 1}}}
    parsed = inject_tool.read_asar_header(_fake_asar(tmp_path, header))
    assert parsed == header


def test_derive_main_anchor_found():
    content = 'xx.handle(yy.SaveMcpToUserDirectory,()=>{})'
    ipc_var, anchor = inject_tool.derive_main_anchor(content)
    assert ipc_var == "xx"
    assert anchor == "xx.handle(yy.SaveMcpToUserDirectory"


def test_derive_main_anchor_missing():
    assert inject_tool.derive_main_anchor("no anchor here") == (None, None)


def test_derive_preload_anchor_found():
    content = (
        'e.contextBridge.exposeInMainWorld("zcode",{a:1});'
        "a.ipcRenderer.invoke('x');a.ipcRenderer.invoke('y');b.ipcRenderer.invoke('z');"
    )
    bridge_var, ipc_var, anchor = inject_tool.derive_preload_anchor(content)
    assert bridge_var == "e"
    assert ipc_var == "a"  # 出现次数最多的 ipcRenderer 变量
    assert anchor == 'e.contextBridge.exposeInMainWorld("zcode",{'


def test_derive_preload_anchor_missing():
    assert inject_tool.derive_preload_anchor("nothing") == (None, None, None)


def test_build_main_patch_uses_ipc_var_and_channels():
    patch = inject_tool.build_main_patch("myIpc")
    assert 'myIpc.handle("zcode:puller:read-provider-config"' in patch
    assert 'myIpc.handle("zcode:puller:fetch-models-from-url"' in patch


def test_build_preload_patch_uses_vars():
    patch = inject_tool.build_preload_patch("bridge", "ipc")
    assert "ipc.ipcRenderer.invoke" in patch
    assert "readProviderConfigFile" in patch


# ---------------------------------------------------------------- zcode_sync

def test_provider_model_ids_dedup_and_order():
    pcfg = {"personalModelIds": ["a", "b", "a", " ", ""], "modelOrder": ["b", "c"]}
    assert zcode_sync.provider_model_ids(pcfg) == ["a", "b", "c"]


def test_provider_model_ids_empty():
    assert zcode_sync.provider_model_ids({}) == []


def test_list_providers_filters_non_api_key():
    config = {
        "config": {
            "providerConfigRules": {
                "providerRules": [
                    {"providerId": "ok", "config": {"access": {"type": "api-key"},
                                                    "api": {"baseUrl": "https://example.com"}}},
                    {"providerId": "oauth", "config": {"access": {"type": "oauth"},
                                                       "api": {"baseUrl": "https://example.com"}}},
                    {"providerId": "nourl", "config": {"access": {"type": "api-key"}, "api": {}}},
                    "not-a-dict",
                ]
            }
        }
    }
    rules = zcode_sync.list_providers(config)
    assert [r["providerId"] for r in rules] == ["ok"]


def test_add_models_to_rule_appends_and_copies_template():
    rule = {"providerId": "p1", "config": {}}
    config_data = {
        "config": {
            "modelConfigRules": {
                "providerModelRules": [
                    {"providerId": "p1", "modelId": "m0", "config": {"temperature": 0.5}},
                ]
            }
        }
    }
    zcode_sync.add_models_to_rule(config_data, rule, ["m1", "m0"])
    assert rule["config"]["personalModelIds"] == ["m1", "m0"]
    assert rule["config"]["modelOrder"] == ["m1", "m0"]
    rules = config_data["config"]["modelConfigRules"]["providerModelRules"]
    assert len(rules) == 2  # m0 已声明不重复添加，只新增 m1
    added = [r for r in rules if r["modelId"] == "m1"]
    assert added and added[0]["config"] == {"temperature": 0.5}
    assert added[0]["config"] is not rules[0]["config"]  # 是深拷贝，不是同一对象


# ---------------------------------------------------------------- watch_*

def test_file_signature_and_missing(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("hello", encoding="utf-8")
    size, mtime_ns = watch_reinstall.file_signature(target)
    assert size == 5
    assert mtime_ns == target.stat().st_mtime_ns
    assert watch_reinstall.file_signature(tmp_path / "missing") is None


def test_sha256_file(tmp_path):
    target = tmp_path / "f.bin"
    target.write_bytes(b"abc")
    assert watch_reinstall.sha256_file(target) == hashlib.sha256(b"abc").hexdigest()


def test_watch_read_header_roundtrip(tmp_path):
    header = {"files": {"b.js": {"size": 2}}}
    raw, parsed = watch_reinstall.read_header(_fake_asar(tmp_path, header))
    assert parsed == header
    assert json.loads(raw) == header


def test_build_path_env_contains_fallback_dirs():
    env = watch_agent.build_path_env()
    assert "/usr/bin" in env.split(":")
    assert "/bin" in env.split(":")
