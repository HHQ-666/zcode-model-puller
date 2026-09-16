#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 更新守护的 launchd 托管工具

把 watch_reinstall.py 注册为 LaunchAgent：
  - RunAtLoad     登录后自动生效
  - WatchPaths    监听 ZCode 应用包与 app.asar 的变化（更新时立即触发）
  - StartInterval 每 5 分钟兜底检查一次

用法：
  python3 watch_agent.py install   # 安装并加载
  python3 watch_agent.py remove    # 卸载
  python3 watch_agent.py status    # 查看状态
"""

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

LABEL = "com.zcode-model-puller.watcher"
TOOL_DIR = Path(__file__).resolve().parent
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
STATE_DIR = Path.home() / ".zcode-model-puller"
LOG_FILE = STATE_DIR / "watch.log"
WATCHER = TOOL_DIR / "watch_reinstall.py"
APP_PATH = Path("/Applications/ZCode.app")
ASAR_FILE = APP_PATH / "Contents" / "Resources" / "app.asar"
DOMAIN = f"gui/{os.getuid()}"


def launchctl(*args):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def build_path_env():
    """launchd 的 PATH 极简，需把 python/node/npx 所在目录显式带上。"""
    dirs = []
    for exe in ("python3", "node", "npx"):
        found = shutil.which(exe)
        if found:
            dirs.append(str(Path(found).resolve().parent))
    dirs += ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]

    seen, ordered = set(), []
    for path in dirs:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ":".join(ordered)


def write_plist():
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(WATCHER)],
        "WatchPaths": [str(ASAR_FILE), str(APP_PATH)],
        "StartInterval": 300,
        "RunAtLoad": True,
        "EnvironmentVariables": {"PATH": build_path_env()},
        "StandardOutPath": str(LOG_FILE),
        "StandardErrorPath": str(LOG_FILE),
        # 不设 ProcessType=Background：那会让 macOS 大幅推迟 StartInterval 兜底检查
    }
    with open(PLIST_PATH, "wb") as fh:
        plistlib.dump(payload, fh)
    return PLIST_PATH


def install():
    if not WATCHER.exists():
        print(f"❌ 找不到守护脚本: {WATCHER}")
        return 1

    path = write_plist()
    print(f"✅ 已写入 LaunchAgent: {path}")

    launchctl("bootout", f"{DOMAIN}/{LABEL}")  # 已存在时先卸载，忽略报错
    result = launchctl("bootstrap", DOMAIN, str(path))
    if result.returncode != 0:
        fallback = launchctl("load", "-w", str(path))
        if fallback.returncode != 0:
            print(f"❌ 加载失败: {result.stderr.strip() or fallback.stderr.strip()}")
            return 1

    seed = subprocess.run([sys.executable, str(WATCHER), "--seed"], capture_output=True, text=True)
    if seed.returncode != 0:
        print(f"ℹ️ 初始指纹记录失败（不影响使用）: {seed.stderr.strip()}")

    print("✅ 更新守护已启用：ZCode 更新后会自动重新注入，并弹出系统通知")
    print(f"   日志: {LOG_FILE}")
    print(f"   停用: python3 {TOOL_DIR / 'watch_agent.py'} remove")
    return 0


def remove():
    result = launchctl("bootout", f"{DOMAIN}/{LABEL}")
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
    if result.returncode == 0:
        print("✅ 更新守护已停用并移除")
    else:
        print("ℹ️ 更新守护未在运行（已清理配置文件）")
    return 0


def status():
    if not PLIST_PATH.exists():
        print("⚠️ 更新守护：未安装")
        return 0

    result = launchctl("print", f"{DOMAIN}/{LABEL}")
    if result.returncode != 0:
        print("⚠️ 更新守护：已安装但未加载")
        print(f"   重新加载: python3 {TOOL_DIR / 'watch_agent.py'} install")
        return 0

    print("✅ 更新守护：已安装并加载")
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith(("state =", "runs =", "last exit code =", "path =")):
            print(f"   {stripped}")
    print(f"   日志: {LOG_FILE}")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "install":
        sys.exit(install())
    if action == "remove":
        sys.exit(remove())
    sys.exit(status())