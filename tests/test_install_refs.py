# 部署一致性测试：install.sh / uninstall.sh 引用的每个文件都必须真实存在。
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_PATTERN = re.compile(r"\$\{SCRIPT_DIR\}/([A-Za-z0-9_.\-/]+)")


def _refs(script_name):
    text = (ROOT / script_name).read_text(encoding="utf-8")
    return REF_PATTERN.findall(text)


def test_install_sh_references_exist():
    refs = _refs("install.sh")
    assert refs, "install.sh 应至少引用一个 SCRIPT_DIR 文件"
    for ref in refs:
        assert (ROOT / ref).is_file(), f"install.sh 引用了不存在的文件：{ref}"


def test_uninstall_sh_references_exist():
    refs = _refs("uninstall.sh")
    assert refs, "uninstall.sh 应至少引用一个 SCRIPT_DIR 文件"
    for ref in refs:
        assert (ROOT / ref).is_file(), f"uninstall.sh 引用了不存在的文件：{ref}"


def test_entry_points_present():
    # 安装/卸载链路的两个入口脚本
    assert (ROOT / "inject_tool.py").is_file()
    assert (ROOT / "watch_agent.py").is_file()
    # inject_tool 运行时读取的注入脚本必须与仓库同目录存在
    assert (ROOT / "zcode-model-puller.js").is_file()
