#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 更新守护

ZCode 每次更新都会整包替换 app.asar，注入的「自动拉取模型」按钮会随之消失。
本脚本由 launchd 触发（监听 app.asar 变化 + 定时兜底），检测到更新后自动重新注入。

判定顺序：
  1. app.asar 必须处于稳定且完整的状态（大小稳定 + 归档头部可解析），避免更新写入途中误判
  2. 与 state.json 中记录的指纹比对，无变化立即静默退出
  3. 包内已带注入标记（无需处理）时只更新指纹
  4. 否则调用 inject_tool.py 重新注入，成功后更新指纹并发出系统通知

用法：
  python3 watch_reinstall.py          # 由 launchd 调用
  python3 watch_reinstall.py --seed   # 仅记录当前指纹（安装完立即调用，避免首次空转）
"""

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".zcode-model-puller"
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "watch.log"
INJECT_LOCK = STATE_DIR / "inject.lock"

RESOURCES_DIR = Path("/Applications/ZCode.app/Contents/Resources")
ASAR_FILE = RESOURCES_DIR / "app.asar"
INFO_PLIST = Path("/Applications/ZCode.app/Contents/Info.plist")
INJECTION_MARKER = "zcode-model-puller.js"


def log(message):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    # launchd 已把 stdout 重定向到同一个日志文件，此时不再重复打印
    if sys.stdout.isatty():
        print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def file_signature(path):
    """(大小, mtime) 快照，用于跳过未变化时的全量哈希。"""
    try:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns
    except OSError:
        return None


def notify(message):
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{message}" with title "ZCode Model Puller"'],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def app_version():
    try:
        import plistlib

        with open(INFO_PLIST, "rb") as fh:
            return plistlib.load(fh).get("CFBundleShortVersionString", "unknown")
    except Exception:
        return "unknown"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_header(asar_path):
    """只读取归档头部（约几 MB），返回 (原始 JSON 文本, 解析后的 dict)。"""
    with open(asar_path, "rb") as fh:
        head = fh.read(16)
        json_len = int.from_bytes(head[8:12], "little")
        if not 0 < json_len < 64 * 1024 * 1024:
            raise ValueError("归档头部长度异常")
        raw = fh.read(json_len).decode("utf-8", errors="replace")
    return raw, json.JSONDecoder().raw_decode(raw)[0]


def asar_is_ready(asar_path):
    """确认更新已写完：文件大小稳定，且归档头部可解析并包含关键目录。"""
    try:
        size_before = asar_path.stat().st_size
    except OSError:
        return False
    time.sleep(3)
    try:
        if asar_path.stat().st_size != size_before or size_before < 1024:
            return False
    except OSError:
        return False

    try:
        _, header = read_header(asar_path)
    except Exception:
        return False

    out = header.get("files", {}).get("out", {}).get("files", {})
    return all(key in out for key in ("main", "preload", "renderer"))


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(**values):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    state.update(values)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE_FILE)
    return state


def seed():
    """记录当前 app.asar 指纹，不做注入。"""
    if not ASAR_FILE.exists():
        return 1
    save_state(
        asar_sha256=sha256_file(ASAR_FILE),
        app_version=app_version(),
        recorded_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        source="seed",
        **signature_fields(ASAR_FILE),
    )
    print("已记录当前 app.asar 指纹")
    return 0


def signature_fields(path):
    signature = file_signature(path)
    if signature is None:
        return {}
    return {"asar_size": signature[0], "asar_mtime_ns": signature[1]}


def acquire_inject_lock():
    """与手动运行注入器互斥：拿不到锁说明已有注入在进行。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(INJECT_LOCK, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def run_injection():
    env = dict(os.environ)
    env["ZCODE_PULLER_INJECT_LOCK_HELD"] = "1"
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "inject_tool.py")],
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def wait_until_ready(timeout=120, interval=15):
    """更新替换整个应用包时，app.asar 会短时间不存在或写入中，这里等它稳定下来。"""
    deadline = time.time() + timeout
    while True:
        if ASAR_FILE.exists() and asar_is_ready(ASAR_FILE):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(interval)


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if not ASAR_FILE.exists() and not wait_until_ready():
        log("等待超时：仍找不到 app.asar，本次跳过")
        return 0

    # 快路径：大小与 mtime 跟上一次处理后一致，直接静默退出（定时轮询不必重复读 300MB）
    state = load_state()
    signature = file_signature(ASAR_FILE)
    if (
        signature
        and state.get("asar_sha256")
        and state.get("asar_size") == signature[0]
        and state.get("asar_mtime_ns") == signature[1]
    ):
        return 0

    if not asar_is_ready(ASAR_FILE) and not wait_until_ready():
        log("app.asar 长时间处于更新写入状态（大小变动或头部不可解析），本次跳过")
        return 0

    try:
        header_raw, _ = read_header(ASAR_FILE)
    except Exception as exc:
        log(f"读取归档头部失败：{exc}")
        return 0

    digest = sha256_file(ASAR_FILE)
    if state.get("asar_sha256") == digest:
        save_state(**signature_fields(ASAR_FILE))  # 内容未变，只刷新时间戳
        return 0

    version = app_version()

    if INJECTION_MARKER in header_raw:
        save_state(
            asar_sha256=digest,
            app_version=version,
            recorded_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            source="already-injected",
            **signature_fields(ASAR_FILE),
        )
        log(f"检测到已注入的构建（ZCode {version}），仅更新指纹")
        return 0

    log(f"检测到 ZCode 更新（当前版本 {version}，app.asar 已变化且未注入），开始自动重新注入...")

    lock = acquire_inject_lock()
    if lock is None:
        log("已有注入任务在进行，跳过本次")
        return 0

    try:
        result = run_injection()
    finally:
        lock.close()

    if result.returncode == 0:
        save_state(
            asar_sha256=sha256_file(ASAR_FILE),
            app_version=version,
            recorded_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            source="auto-reinstall",
            **signature_fields(ASAR_FILE),
        )
        log(f"自动重新注入成功（ZCode {version}）")
        notify("ZCode 更新后已自动重新注入「自动拉取模型」，重启 ZCode 后按钮即恢复")
        return 0

    detail = (result.stdout or "")[-1500:] + (result.stderr or "")[-1500:]
    log(f"自动重新注入失败（退出码 {result.returncode}）：{detail}")
    notify("ZCode 更新后自动注入失败，请手动运行 install.sh")
    return 1


if __name__ == "__main__":
    if "--seed" in sys.argv:
        sys.exit(seed())
    sys.exit(main())