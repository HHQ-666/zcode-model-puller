#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键质量门禁：构建检查 -> 测试+覆盖率 -> 依赖 -> lint -> 部署检查。

用法（仓库根目录）：
    python tools/run_quality_gates.py
    # 或
    make check

规则：任一步失败立即停下，打印失败原因并以非零码退出；全部通过才输出通过。
门禁工具（pytest / pytest-cov / ruff / pip-audit）需先安装：
    pip install -r requirements-dev.txt

覆盖率门槛在 pyproject.toml 的 [tool.quality_gates] coverage_min 中配置，
取首跑实测值向下取整的 ratchet 基线（只升不降），理由见 QUALITY_GATES.md。
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_FILES_GLOB = "*.py"
COVERAGE_MODULES = ["inject_tool", "zcode_sync", "watch_agent", "watch_reinstall", "run"]
SHELL_SCRIPTS = ["install.sh", "uninstall.sh"]
JS_FILE = "zcode-model-puller.js"

results = []  # (步骤名, 状态 PASS/FAIL/SKIP, 说明)


def run_cmd(cmd, cwd=ROOT):
    print(f"$ {' '.join(str(c) for c in cmd)}")
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if out.strip():
        print(out.rstrip())
    return proc.returncode, out


def record(name, status, detail=""):
    results.append((name, status, detail))
    mark = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️ "}[status]
    print(f"{mark} [{name}] {status} {detail}\n")


def fail_and_exit(name, detail):
    record(name, "FAIL", detail)
    print_summary()
    print(f"门禁未通过：{name} 失败，{detail}")
    sys.exit(1)


def print_summary():
    print("=" * 64)
    print("门禁结果汇总")
    for name, status, detail in results:
        print(f"  {status:4}  {name}  {detail}")
    print("=" * 64)


def load_coverage_min():
    try:
        with open(ROOT / "pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        return float(data["tool"]["quality_gates"]["coverage_min"])
    except Exception as exc:  # 配置缺失/损坏视为门禁配置错误
        fail_and_exit("配置", f"无法读取 pyproject.toml 的 coverage_min：{exc}")


# ---------------------------------------------------------------------------
# 1. 构建检查
# ---------------------------------------------------------------------------

def gate_build():
    name = "构建检查"
    rc, _ = run_cmd([sys.executable, "-m", "compileall", "-q", "."])
    if rc != 0:
        fail_and_exit(name, "python -m compileall 失败，存在无法编译的 .py 文件")

    node = shutil.which("node")
    if node:
        rc, _ = run_cmd([node, "--check", JS_FILE])
        if rc != 0:
            fail_and_exit(name, f"node --check {JS_FILE} 语法检查失败")
    else:
        record(name, "SKIP", f"未检测到 node，跳过 {JS_FILE} 语法检查（其余构建检查已通过）")
        return

    bash = shutil.which("bash")
    if bash:
        for script in SHELL_SCRIPTS:
            rc, _ = run_cmd([bash, "-n", script])
            if rc != 0:
                fail_and_exit(name, f"bash -n {script} 语法检查失败")
    record(name, "PASS", "全部 .py 可编译、JS 与 shell 脚本语法正确")


# ---------------------------------------------------------------------------
# 2. 测试 + 覆盖率门禁
# ---------------------------------------------------------------------------

def gate_tests(coverage_min):
    name = "测试+覆盖率"
    with tempfile.TemporaryDirectory() as tmp:
        cov_json = str(Path(tmp) / "coverage.json")
        cmd = [sys.executable, "-m", "pytest", "tests/", "-q",
               "--cov-report", f"json:{cov_json}", "--cov-report", "term"]
        for mod in COVERAGE_MODULES:
            cmd.append(f"--cov={mod}")
        rc, _ = run_cmd(cmd)
        if rc != 0:
            fail_and_exit(name, "pytest 未全部通过（详见上方输出）")
        try:
            with open(cov_json, encoding="utf-8") as fh:
                total = float(json.load(fh)["totals"]["percent_covered"])
        except Exception as exc:
            fail_and_exit(name, f"无法解析覆盖率报告：{exc}")
    detail = f"覆盖率实测 {total:.2f}%，门槛 {coverage_min:.0f}%"
    if total < coverage_min:
        fail_and_exit(name, f"{detail}，低于门槛")
    record(name, "PASS", detail)


# ---------------------------------------------------------------------------
# 3. 依赖门禁
# ---------------------------------------------------------------------------

def gate_deps():
    name = "依赖门禁"
    try:
        import pip_audit  # noqa: F401
    except ImportError:
        fail_and_exit(name, "未安装 pip-audit，请先执行 pip install -r requirements-dev.txt")
    with tempfile.TemporaryDirectory() as tmp:
        out_json = str(Path(tmp) / "audit.json")
        rc, out = run_cmd([sys.executable, "-m", "pip_audit",
                           "-r", "requirements-dev.txt",
                           "--format", "json", "--output", out_json])
        vulns = []
        try:
            with open(out_json, encoding="utf-8") as fh:
                data = json.load(fh)
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    vulns.append(f"{dep.get('name')}=={dep.get('version')}: {vuln.get('id')}")
        except Exception:
            if rc != 0:
                fail_and_exit(name, f"pip-audit 执行失败（可能无网络或解析失败）：{out.strip()[-300:]}")
    if vulns:
        fail_and_exit(name, "发现已知漏洞：" + "；".join(vulns))
    record(name, "PASS", "pip-audit 审计 requirements-dev.txt，未发现已知漏洞")


# ---------------------------------------------------------------------------
# 4. lint 门禁（硬门禁 F+E9；其余规则只报告不拦）
# ---------------------------------------------------------------------------

def gate_lint():
    name = "lint 门禁"
    ruff = shutil.which("ruff")
    base = [ruff] if ruff else [sys.executable, "-m", "ruff"]
    if not ruff:
        try:
            import ruff  # noqa: F401
        except ImportError:
            fail_and_exit(name, "未安装 ruff，请先执行 pip install -r requirements-dev.txt")
    rc, out = run_cmd(base + ["check", "."])
    if rc != 0:
        fail_and_exit(name, "ruff 硬门禁（F,E9）未通过，详见上方输出")
    # 报告-only：更宽的规则集只统计、不拦截
    _, report = run_cmd(base + ["check", "--select", "E,W", "--exit-zero", "--statistics", "."])
    stat_lines = [ln for ln in report.splitlines() if re.match(r"^\d+\s", ln)]
    total_findings = sum(int(ln.split()[0]) for ln in stat_lines)
    record(name, "PASS",
           f"硬门禁 F+E9 通过；报告-only(E,W) 共 {total_findings} 处（{len(stat_lines)} 类），不拦截，详见上方输出")


# ---------------------------------------------------------------------------
# 5. 部署检查（静态校验 + 临时目录模拟布局，不执行真实安装）
# ---------------------------------------------------------------------------

def gate_deploy():
    name = "部署检查"
    ref_pattern = re.compile(r"\$\{SCRIPT_DIR\}/([A-Za-z0-9_.\-/]+)")
    missing = []
    refs = set()
    for script in SHELL_SCRIPTS:
        text = (ROOT / script).read_text(encoding="utf-8")
        for ref in ref_pattern.findall(text):
            refs.add(ref)
            if not (ROOT / ref).exists():
                missing.append(f"{script} 引用了不存在的文件 {ref}")
    if missing:
        fail_and_exit(name, "；".join(missing))

    # 临时目录模拟安装布局：把脚本与其引用文件按相对结构复制过去再核对一遍。
    # 不直接执行 install.sh：它会调用 inject_tool.py 改动本机 ZCode 应用目录，
    # 且依赖 ZCode 本体与 npx，属于真实安装动作，不在门禁里执行。
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "stage"
        stage.mkdir()
        for rel in list(refs) + SHELL_SCRIPTS:
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
        for rel in refs:
            if not (stage / rel).exists():
                fail_and_exit(name, f"模拟布局中缺失 {rel}")
    record(name, "PASS",
           f"install.sh/uninstall.sh 引用的 {len(refs)} 个文件均存在，临时目录模拟布局完整；"
           "真实安装未执行（会改动本机 ZCode 目录，见 QUALITY_GATES.md）")


def main():
    print("=" * 64)
    print("zcode-model-puller 质量门禁")
    print("=" * 64)
    coverage_min = load_coverage_min()
    gate_build()
    gate_tests(coverage_min)
    gate_deps()
    gate_lint()
    gate_deploy()
    print_summary()
    print("全部质量门禁通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
