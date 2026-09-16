#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 界面注入与还原管理工具
- 在 main 进程注入原生安全的 provider_config 读写与网络代理 IPC
- 在 preload 进程挂载 window.zcode 官方 API 扩展
- 在 renderer 进程注入一键「自动拉取模型」按钮与选择弹窗
- 保留官方原始完整备份，随时可一键还原

适配 ZCode 3.12+：自定义供应商配置由 config.json 迁移至 provider_config.json，
压缩产物中的变量名会随版本变化，因此所有注入锚点均动态推导，不再写死。
"""

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ZCODE_APP = Path("/Applications/ZCode.app")
RESOURCES_DIR = ZCODE_APP / "Contents" / "Resources"
ASAR_FILE = RESOURCES_DIR / "app.asar"
ASAR_BAK_FILE = RESOURCES_DIR / "app.asar.original.bak"
UNPACKED_DIR = RESOURCES_DIR / "app.asar.unpacked"

SCRIPT_DIR = Path(__file__).resolve().parent
PULLER_JS_FILE = SCRIPT_DIR / "zcode-model-puller.js"

WORK_DIR = Path("/tmp/zcode_inject_build")
TEMP_ASAR = Path("/tmp/zcode_repacked.asar")
INJECT_LOCK = Path.home() / ".zcode-model-puller" / "inject.lock"

# 需要保持解包（unpacked）的原生模块：单个 glob 必须同时覆盖 .node 与 spawn-helper，
# 因为 asar CLI 重复传 --unpack 只会保留最后一个。
UNPACK_GLOBS = ["**/*{node,spawn-helper}"]

IPC_READ = "zcode:puller:read-provider-config"
IPC_WRITE = "zcode:puller:write-provider-config"
IPC_FETCH = "zcode:puller:fetch-models-from-url"

PROVIDER_CONFIG_RELATIVE = [".zcode", "v2", "provider_config.json"]


def run(cmd, **kwargs):
    res = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if res.returncode != 0:
        print(f"❌ 命令执行失败: {' '.join(str(c) for c in cmd)}")
        print(res.stderr.strip() or res.stdout.strip())
    return res


def check_prerequisites():
    if not ZCODE_APP.exists():
        print(f"❌ 找不到 ZCode 应用程序: {ZCODE_APP}")
        return False
    if not ASAR_FILE.exists():
        print(f"❌ 找不到 ZCode 核心资源: {ASAR_FILE}")
        return False
    if not PULLER_JS_FILE.exists():
        print(f"❌ 找不到注入脚本源码: {PULLER_JS_FILE}")
        return False
    return True


def backup_asar():
    if not ASAR_BAK_FILE.exists():
        print("📦 正在创建原始 app.asar 完整备份 (仅首次执行)...")
        shutil.copy2(ASAR_FILE, ASAR_BAK_FILE)
        print(f"  ✅ 备份已保存至: {ASAR_BAK_FILE}")
    else:
        print(f"  ℹ️ 已存在原版备份: {ASAR_BAK_FILE}")


def restore_asar():
    if not ASAR_BAK_FILE.exists():
        print(f"❌ 找不到原始备份文件: {ASAR_BAK_FILE}")
        return False
    print("🔄 正在还原 ZCode 核心包至原版...")
    shutil.copy2(ASAR_BAK_FILE, ASAR_FILE)
    print("🎉 还原成功！ZCode 已恢复至原版状态。")
    print("💡 请完全退出并重新打开 ZCode 即可生效。")
    return True


# --------------------------------------------------------------------------
# 锚点推导：压缩后的变量名随版本变化，这里全部动态识别
# --------------------------------------------------------------------------

def derive_main_anchor(content: str):
    """返回 (ipcMain 变量名, 锚点字符串)。"""
    match = re.search(r'([A-Za-z_$][\w$]*)\.handle\(([A-Za-z_$][\w$]*)\.SaveMcpToUserDirectory', content)
    if not match:
        return None, None
    ipc_var = match.group(1)
    return ipc_var, match.group(0)


def derive_preload_anchor(content: str):
    """返回 (contextBridge 变量名, ipcRenderer 变量名, 锚点字符串)。"""
    match = re.search(r'([A-Za-z_$][\w$]*)\.contextBridge\.exposeInMainWorld\("zcode",\{', content)
    if not match:
        return None, None, None
    bridge_var = match.group(1)

    counter = {}
    for var in re.findall(r'([A-Za-z_$][\w$]*)\.ipcRenderer\.invoke', content):
        counter[var] = counter.get(var, 0) + 1
    if not counter:
        return None, None, None
    ipc_renderer_var = max(counter.items(), key=lambda kv: kv[1])[0]
    return bridge_var, ipc_renderer_var, match.group(0)


# --------------------------------------------------------------------------
# 被注入的代码片段
# --------------------------------------------------------------------------

def build_main_patch(ipc_var: str) -> str:
    """注入 main 进程 IPC 处理器。用逗号连接，兼容逗号表达式与语句两种上下文。"""
    return (
        f'{ipc_var}.handle("{IPC_READ}",async()=>{{try{{let{{default:f}}=await import("node:fs"),'
        f'{{default:p}}=await import("node:path"),{{default:o}}=await import("node:os"),'
        f'file=p.join(o.homedir(),{json.dumps(PROVIDER_CONFIG_RELATIVE[0])},'
        f'{json.dumps(PROVIDER_CONFIG_RELATIVE[1])},{json.dumps(PROVIDER_CONFIG_RELATIVE[2])});'
        f'return{{success:!0,data:JSON.parse(f.readFileSync(file,"utf-8"))}}}}'
        f'catch(e){{return{{success:!1,error:String(e)}}}}}}),'
        f'{ipc_var}.handle("{IPC_WRITE}",async(e,d)=>{{try{{let{{default:f}}=await import("node:fs"),'
        f'{{default:p}}=await import("node:path"),{{default:o}}=await import("node:os"),'
        f'file=p.join(o.homedir(),{json.dumps(PROVIDER_CONFIG_RELATIVE[0])},'
        f'{json.dumps(PROVIDER_CONFIG_RELATIVE[1])},{json.dumps(PROVIDER_CONFIG_RELATIVE[2])}),'
        f'tmp=file+".puller.tmp";f.writeFileSync(tmp,JSON.stringify(d,null,2),"utf-8");'
        f'try{{f.chmodSync(tmp,384)}}catch{{}}f.renameSync(tmp,file);return{{success:!0}}}}'
        f'catch(e){{return{{success:!1,error:String(e)}}}}}}),'
        f'{ipc_var}.handle("{IPC_FETCH}",async(e,{{baseUrl:u,apiKey:k}})=>{{try{{'
        f'let{{default:ht}}=await import("node:https"),{{default:h}}=await import("node:http");'
        f'let clean=(u||"").trim().replace(/\\/+$/,"");let candidates=[];'
        f'if(clean.endsWith("/v1")){{candidates.push(clean+"/models");candidates.push(clean.replace(/\\/v1$/,"")+"/models")}}'
        f'else{{candidates.push(clean+"/v1/models");candidates.push(clean+"/models")}}'
        f'if(clean.endsWith("/api")){{candidates.unshift(clean+"/v1/models")}}'
        f'for(let cur of candidates){{try{{let res=await new Promise((resolve,reject)=>{{'
        f'let mod=cur.startsWith("https:")?ht:h;let req=mod.request(cur,{{method:"GET",'
        f'headers:{{"User-Agent":"ZCode"'
        f',"Accept":"application/json",...k?{{Authorization:"Bearer "+k.trim(),"x-api-key":k.trim()}}:{{}}}},timeout:8000}},'
        f'r=>{{let b="";r.on("data",c=>b+=c);r.on("end",()=>{{if(r.statusCode>=200&&r.statusCode<300){{'
        f'try{{let j=JSON.parse(b);let l=Array.isArray(j)?j:Array.isArray(j.data)?j.data:Array.isArray(j.models)?j.models:[];'
        f'let ids=[];for(let it of l){{let id=typeof it=="string"?it.trim():(it.id||it.name||"").trim();'
        f'if(id&&!ids.includes(id))ids.push(id)}}if(ids.length>0)return resolve({{success:!0,models:ids}})}}catch(e){{}}}}resolve(null)}})}});'
        f'req.on("error",()=>resolve(null));req.on("timeout",()=>{{req.destroy();resolve(null)}});req.end()}});'
        f'if(res&&res.success)return res}}catch(e){{}}}}'
        f'return{{success:!1,error:"未能获取到模型列表，请检查 Base URL 和 API Key"}}}}'
        f'catch(e){{return{{success:!1,error:String(e)}}}}}}),'
    )


def build_preload_patch(bridge_var: str, ipc_var: str) -> str:
    """注入 preload 桥接方法，紧跟在 exposeInMainWorld("zcode",{ 之后。"""
    return (
        f'readProviderConfigFile:s(()=>{ipc_var}.ipcRenderer.invoke("{IPC_READ}"),"readProviderConfigFile"),'
        f'writeProviderConfigFile:s(t=>{ipc_var}.ipcRenderer.invoke("{IPC_WRITE}",t),"writeProviderConfigFile"),'
        f'fetchModelsFromUrl:s((t,n)=>{ipc_var}.ipcRenderer.invoke("{IPC_FETCH}",{{baseUrl:t,apiKey:n}}),"fetchModelsFromUrl"),'
    )


# --------------------------------------------------------------------------
# 校验辅助
# --------------------------------------------------------------------------

def syntax_check(path: Path, label: str) -> bool:
    """用 node --check 校验注入后的产物语法是否仍然合法。"""
    suffix = ".mjs" if path.suffix == ".js" else path.suffix
    probe = Path("/tmp/zcode_syntax_probe") / (path.stem + suffix)
    probe.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, probe)
    res = subprocess.run(["node", "--check", str(probe)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f" {label} 语法校验未通过:\n{res.stderr.strip()[:800]}")
        return False
    print(f"  ✅ {label} 语法校验通过")
    return True


def read_asar_header(asar_path: Path):
    with open(asar_path, "rb") as fh:
        head = fh.read(16)
        json_len = int.from_bytes(head[8:12], "little")
        raw = fh.read(json_len).decode("utf-8", errors="replace")
    # 头部 JSON 会按 4 字节对齐补位，raw_decode 可忽略尾部填充
    return json.JSONDecoder().raw_decode(raw)[0]


def collect_asar_files(header):
    """把 asar 头部展开成 {相对路径: 条目} 的扁平字典。"""

    def walk(node, prefix=""):
        for name, entry in node.items():
            path = f"{prefix}/{name}" if prefix else name
            if "files" in entry:
                yield from walk(entry["files"], path)
            else:
                yield path, entry

    return dict(walk(header.get("files", {})))


def official_unpacked_files():
    """官方原版中被标记为 unpacked 的文件集合（用于校验我们是否原样保留）。"""
    if not ASAR_BAK_FILE.exists():
        return set()
    entries = collect_asar_files(read_asar_header(ASAR_BAK_FILE))
    return {path for path, entry in entries.items() if entry.get("unpacked")}


def verify_packed_asar(asar_path: Path):
    entries = collect_asar_files(read_asar_header(asar_path))
    unpacked_now = {path for path, entry in entries.items() if entry.get("unpacked")}

    expected_unpacked = official_unpacked_files()
    missing_unpack = sorted(expected_unpacked - unpacked_now)

    checks = {
        "renderer 注入脚本": "out/renderer/zcode-model-puller.js" in entries,
        "原生模块保持 unpacked": not missing_unpack,
    }
    for path in missing_unpack:
        print(f"  ️ 原生模块未被解包: {path}")

    # 内容级校验
    extract_dir = Path("/tmp/zcode_verify_extract")
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    res = run(["npx", "--yes", "@electron/asar", "extract", str(asar_path), str(extract_dir)])
    if res.returncode == 0:
        index_html = extract_dir / "out" / "renderer" / "index.html"
        preload = extract_dir / "out" / "preload" / "index.cjs"
        main = extract_dir / "out" / "main" / "index.js"
        checks["preload 桥接"] = preload.exists() and "readProviderConfigFile" in preload.read_text(
            encoding="utf-8", errors="replace"
        )
        checks["main IPC"] = main.exists() and IPC_READ in main.read_text(encoding="utf-8", errors="replace")
        checks["index.html 入口"] = index_html.exists() and "zcode-model-puller.js" in index_html.read_text(
            encoding="utf-8", errors="replace"
        )
        shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        checks["解包复核"] = False

    ok = all(checks.values())
    for name, passed in checks.items():
        print(f"  {'✅' if passed else '❌'} {name}")
    print(f"  ℹ️ 解包文件数: {len(unpacked_now)}（官方 {len(expected_unpacked)}）")
    return ok


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def acquire_inject_lock():
    """
    与更新守护（watch_reinstall.py）互斥，避免两处同时重新打包 app.asar。
    返回 (是否可继续, 需要释放的句柄)；由守护进程调用时无需重复加锁。
    """
    if os.environ.get("ZCODE_PULLER_INJECT_LOCK_HELD") == "1":
        return True, None
    INJECT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = open(INJECT_LOCK, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        print("❌ 已有注入任务正在进行（可能由更新守护触发），请稍后再试")
        return False, None
    return True, handle


def record_state_for_watcher():
    """记录注入后的指纹，让更新守护知道这个构建已处理过（不影响功能，失败可忽略）。"""
    if os.environ.get("ZCODE_PULLER_INJECT_LOCK_HELD") == "1":
        return  # 由守护进程触发时，它会自己记录
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import watch_reinstall

        watch_reinstall.seed()
    except Exception:
        pass


def install_injection():
    acquired, lock = acquire_inject_lock()
    if not acquired:
        return False
    try:
        return _install_injection_locked()
    finally:
        if lock:
            lock.close()


def _install_injection_locked():
    if not check_prerequisites():
        return False

    backup_asar()

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    print("🚀 正在解压核心包 (app.asar)...")
    res = run(["npx", "--yes", "@electron/asar", "extract", str(ASAR_FILE), str(WORK_DIR)])
    if res.returncode != 0:
        return False

    renderer_dir = WORK_DIR / "out" / "renderer"
    preload_cjs = WORK_DIR / "out" / "preload" / "index.cjs"
    main_js = WORK_DIR / "out" / "main" / "index.js"
    index_html = renderer_dir / "index.html"

    for required in (preload_cjs, main_js, index_html):
        if not required.exists():
            print(f"❌ 解包结果缺少关键文件: {required}")
            return False

    # 1. 前端脚本 + 入口
    shutil.copy2(PULLER_JS_FILE, renderer_dir / "zcode-model-puller.js")
    if not syntax_check(renderer_dir / "zcode-model-puller.js", "renderer 注入脚本"):
        return False
    print("  ✅ 已写入前端注入脚本")

    html_content = index_html.read_text(encoding="utf-8")
    script_tag = '<script type="module" src="./zcode-model-puller.js"></script>'
    if script_tag not in html_content:
        if "</body>" not in html_content:
            print(" index.html 中找不到 </body>，无法挂载入口")
            return False
        html_content = html_content.replace("</body>", f"  {script_tag}\n  </body>")
        index_html.write_text(html_content, encoding="utf-8")
        print("  ✅ 已在 index.html 中挂载启动入口")
    else:
        print("  ℹ️ index.html 已包含启动入口")

    # 2. preload 扩展
    preload_content = preload_cjs.read_text(encoding="utf-8")
    if "readProviderConfigFile" in preload_content:
        print("  ℹ️ preload 已包含官方扩展 API")
    else:
        bridge_var, ipc_var, anchor = derive_preload_anchor(preload_content)
        if not anchor:
            print("❌ 未能在 preload 中定位 contextBridge.exposeInMainWorld(\"zcode\") 锚点")
            return False
        preload_content = preload_content.replace(anchor, anchor + build_preload_patch(bridge_var, ipc_var), 1)
        preload_cjs.write_text(preload_content, encoding="utf-8")
        if not syntax_check(preload_cjs, "preload"):
            return False
        print(f"  ✅ 已在 preload 进程扩展 window.zcode API (ipcRenderer → {ipc_var})")

    # 3. main 进程 IPC
    main_content = main_js.read_text(encoding="utf-8")
    if IPC_READ in main_content:
        print("  ℹ️ main 已包含安全 IPC 处理器")
    else:
        ipc_var, anchor = derive_main_anchor(main_content)
        if not anchor:
            print("❌ 未能在 main 中定位 SaveMcpToUserDirectory 锚点，ZCode 版本结构可能已变化")
            return False
        main_content = main_content.replace(anchor, build_main_patch(ipc_var) + anchor, 1)
        main_js.write_text(main_content, encoding="utf-8")
        if not syntax_check(main_js, "main"):
            return False
        print(f"  ✅ 已在主进程挂载安全 IPC 处理器 (ipcMain → {ipc_var})")

    # 4. 重新打包（原生模块保持解包，避免 node-pty / ssh2 无法加载）
    print("📦 正在重新打包 app.asar...")
    if TEMP_ASAR.exists():
        TEMP_ASAR.unlink()
    pack_cmd = ["npx", "--yes", "@electron/asar", "pack", str(WORK_DIR), str(TEMP_ASAR)]
    for glob in UNPACK_GLOBS:
        pack_cmd += ["--unpack", glob]
    res = run(pack_cmd)
    if res.returncode != 0:
        return False

    print("🔍 正在校验打包结果...")
    if not verify_packed_asar(TEMP_ASAR):
        print("❌ 打包结果校验失败，已放弃替换（原 app.asar 未被修改）")
        return False

    # 记录原 unpacked 目录中各文件的权限，替换后原样还原
    original_modes = {}
    if UNPACKED_DIR.exists():
        for path in UNPACKED_DIR.rglob("*"):
            if path.is_file():
                original_modes[path.relative_to(UNPACKED_DIR).as_posix()] = path.stat().st_mode & 0o777

    shutil.move(str(TEMP_ASAR), str(ASAR_FILE))

    repacked_unpacked = Path(str(TEMP_ASAR) + ".unpacked")
    if repacked_unpacked.exists():
        if UNPACKED_DIR.exists():
            shutil.rmtree(UNPACKED_DIR)
        shutil.move(str(repacked_unpacked), str(UNPACKED_DIR))
        for rel, mode in original_modes.items():
            target = UNPACKED_DIR / rel
            if target.exists():
                os.chmod(target, mode)

    shutil.rmtree(WORK_DIR, ignore_errors=True)
    record_state_for_watcher()

    print("\n🎉 注入成功！")
    print("✨ 本次适配内容：")
    print("   1. 供应商配置迁移至 provider_config.json（ZCode 3.12+ 新结构）")
    print("   2. 注入锚点动态推导，不再依赖压缩后的变量名")
    print("   3. 保持 node-pty / ssh2 原生模块 unpacked，终端功能不受影响")
    print("   4. 写入后由 host 轮询自动重载，模型列表 UI 自动刷新")
    print("💡 请完全退出并重新打开 ZCode（Command + Q 退出后再启动）即可体验！")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--restore", "--uninstall", "-r"]:
        restore_asar()
    else:
        sys.exit(0 if install_injection() else 1)