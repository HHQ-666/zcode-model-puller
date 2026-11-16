# 冒烟测试：模块可导入、全部 .py 可编译、关键资产存在。
# 只做离线验证，不访问网络、不依赖本机是否装有 ZCode。
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUSINESS_MODULES = ["inject_tool", "zcode_sync", "watch_agent", "watch_reinstall", "run"]


def test_all_python_files_compile():
    py_files = sorted(ROOT.glob("*.py")) + [ROOT / "tools" / "run_quality_gates.py"]
    assert py_files, "仓库根目录应有 .py 文件"
    for path in py_files:
        py_compile.compile(str(path), doraise=True)


def test_business_modules_importable():
    import importlib

    for name in BUSINESS_MODULES:
        module = importlib.import_module(name)
        assert module is not None


def test_key_assets_exist():
    for rel in ["zcode-model-puller.js", "install.sh", "uninstall.sh", "README.md", "LICENSE"]:
        assert (ROOT / rel).is_file(), f"缺失关键文件 {rel}"
