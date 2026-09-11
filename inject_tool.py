#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 界面注入与还原管理工具 (终极完美版)
- 在 main 进程注入原生安全的 config 读写与网络代理 IPC，彻底消除“通信桥不可用”报错
- 在 preload 进程挂载 window.zcode 官方 API 扩展
- 在 renderer 进程注入不重绘、不跳顶部的精致选择弹窗与一键自动拉取按钮
- 保留官方原始完整备份，随时可一键还原
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ZCODE_APP = Path("/Applications/ZCode.app")
RESOURCES_DIR = ZCODE_APP / "Contents" / "Resources"
ASAR_FILE = RESOURCES_DIR / "app.asar"
ASAR_BAK_FILE = RESOURCES_DIR / "app.asar.original.bak"

SCRIPT_DIR = Path(__file__).resolve().parent
PULLER_JS_FILE = SCRIPT_DIR / "zcode-model-puller.js"


def check_prerequisites():
    if not ZCODE_APP.exists():
        print(f"❌ 找不到 ZCode 应用程序: {ZCODE_APP}")
        return False
    if not ASAR_FILE.exists() and not ASAR_BAK_FILE.exists():
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


def install_injection():
    if not check_prerequisites():
        return False

    backup_asar()

    work_dir = Path("/tmp/zcode_inject_build")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 正在解压核心包 (app.asar)...")
    cmd_extract = [
        "npx", "@electron/asar", "extract",
        str(ASAR_FILE),
        str(work_dir)
    ]
    res = subprocess.run(cmd_extract, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ 解包失败: {res.stderr}")
        return False

    # 1. 复制 zcode-model-puller.js 到 out/renderer
    renderer_dir = work_dir / "out" / "renderer"
    target_js = renderer_dir / "zcode-model-puller.js"
    shutil.copy2(PULLER_JS_FILE, target_js)
    print("  ✅ 已写入前端注入脚本 (终极交互版，解决滚动条跳顶)")

    # 2. 修改 out/renderer/index.html 引入脚本
    index_html = renderer_dir / "index.html"
    if index_html.exists():
        html_content = index_html.read_text(encoding="utf-8")
        script_tag = '<script type="module" src="./zcode-model-puller.js"></script>'
        if script_tag not in html_content:
            html_content = html_content.replace("</body>", f"  {script_tag}\n  </body>")
            index_html.write_text(html_content, encoding="utf-8")
            print("  ✅ 已在 index.html 中挂载启动入口")
        else:
            print("  ℹ️ index.html 已包含启动入口")

    # 3. 在 preload/index.cjs 中扩展 window.zcode 的原生安全 IPC 方法
    preload_cjs = work_dir / "out" / "preload" / "index.cjs"
    if preload_cjs.exists():
        preload_content = preload_cjs.read_text(encoding="utf-8")
        target_preload = 'contextBridge.exposeInMainWorld("zcode",{'
        patch_preload = (
            target_preload +
            'readConfigFile:s(()=>h.ipcRenderer.invoke("zcode:read-model-config"),"readConfigFile"),' +
            'writeConfigFile:s(t=>h.ipcRenderer.invoke("zcode:write-model-config",t),"writeConfigFile"),' +
            'fetchModelsFromUrl:s((t,n)=>h.ipcRenderer.invoke("zcode:fetch-models-from-url",{baseUrl:t,apiKey:n}),"fetchModelsFromUrl"),'
        )
        if target_preload in preload_content and "readConfigFile" not in preload_content:
            preload_content = preload_content.replace(target_preload, patch_preload, 1)
            preload_cjs.write_text(preload_content, encoding="utf-8")
            print("  ✅ 已在 preload 进程无缝扩展 window.zcode 官方 API")
        else:
            print("  ℹ️ preload 已包含官方扩展 API")

    # 4. 在 main/index.js 中注册对应的安全 IPC 处理器
    main_js = work_dir / "out" / "main" / "index.js"
    if main_js.exists():
        main_content = main_js.read_text(encoding="utf-8")
        target_main = "he.handle(I.SaveMcpToUserDirectory"
        patch_main = (
            '\nhe.handle("zcode:read-model-config",async()=>{try{let{default:f}=await import("node:fs"),{default:p}=await import("node:path"),{default:o}=await import("node:os");let c=f.readFileSync(p.join(o.homedir(),".zcode","v2","config.json"),"utf-8");return{success:!0,data:JSON.parse(c)}}catch(e){return{success:!1,error:String(e)}}});\n'
            'he.handle("zcode:write-model-config",async(e,d)=>{try{let{default:f}=await import("node:fs"),{default:p}=await import("node:path"),{default:o}=await import("node:os");f.writeFileSync(p.join(o.homedir(),".zcode","v2","config.json"),JSON.stringify(d,null,2),"utf-8");return{success:!0}}catch(e){return{success:!1,error:String(e)}}});\n'
            'he.handle("zcode:fetch-models-from-url",async(e,{baseUrl:u,apiKey:k})=>{try{let{default:ht}=await import("node:https"),{default:h}=await import("node:http");let clean=(u||"").trim().replace(/\\/+$/,"");let candidates=[];if(clean.endsWith("/v1")){candidates.push(clean+"/models");candidates.push(clean.replace(/\\/v1$/,"")+"/models")}else{candidates.push(clean+"/v1/models");candidates.push(clean+"/models")}if(clean.endsWith("/api")){candidates.unshift(clean+"/v1/models")}for(let cur of candidates){try{let res=await new Promise((resolve,reject)=>{let mod=cur.startsWith("https:")?ht:h;let req=mod.request(cur,{method:"GET",headers:{"User-Agent":"ZCode/3.11.2","Accept":"application/json",...k?{Authorization:"Bearer "+k.trim(),"x-api-key":k.trim()}:{}},timeout:8000},r=>{let b="";r.on("data",c=>b+=c);r.on("end",()=>{if(r.statusCode>=200&&r.statusCode<300){try{let j=JSON.parse(b);let l=Array.isArray(j)?j:Array.isArray(j.data)?j.data:Array.isArray(j.models)?j.models:[];let ids=[];for(let it of l){let id=typeof it=="string"?it.trim():(it.id||it.name||"").trim();if(id&&!ids.includes(id))ids.push(id)}if(ids.length>0)return resolve({success:!0,models:ids})}catch(e){}}resolve(null)})});req.on("error",()=>resolve(null));req.on("timeout",()=>{req.destroy();resolve(null)});req.end()});if(res&&res.success)return res}catch(e){}}return{success:!1,error:"未能获取到模型列表，请检查 Base URL 和 API Key"}}catch(e){return{success:!1,error:String(e)}}});\n'
            + target_main
        )
        if target_main in main_content and "zcode:read-model-config" not in main_content:
            main_content = main_content.replace(target_main, patch_main, 1)
            main_js.write_text(main_content, encoding="utf-8")
            print("  ✅ 已在主进程挂载安全 IPC 处理器 (支持 node:fs 和 node:https)")
        else:
            print("  ℹ️ main 已包含安全 IPC 处理器")

    # 5. 重新打包 app.asar
    print("📦 正在重新打包 app.asar...")
    temp_packed_asar = Path("/tmp/zcode_repacked.asar")
    if temp_packed_asar.exists():
        temp_packed_asar.unlink()

    cmd_pack = [
        "npx", "@electron/asar", "pack",
        str(work_dir),
        str(temp_packed_asar)
    ]
    res_pack = subprocess.run(cmd_pack, capture_output=True, text=True)
    if res_pack.returncode != 0:
        print(f"❌ 打包失败: {res_pack.stderr}")
        return False

    # 替换目标 app.asar
    shutil.move(temp_packed_asar, ASAR_FILE)
    shutil.rmtree(work_dir, ignore_errors=True)

    print("\n🎉 恭喜！终极版注入成功！")
    print("✨ 已彻底解决：")
    print("   1. 勾选模型时页面回到顶部问题（采用就地切换，滚动条位置丝毫不动）")
    print("   2. 彻底解决「配置文件通信桥不可用」报错（通过 Electron 原生 IPC 完美读写）")
    print("   3. 自动识别已有模型和新模型")
    print("   4. 保存后自动平滑刷新界面呈现新模型")
    print("💡 请完全退出并重新打开 ZCode（Command + Q 退出后再启动）即可体验！")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--restore", "--uninstall", "-r"]:
        restore_asar()
    else:
        install_injection()
