# 让 pytest 能从仓库根目录导入业务模块（仓库为扁平结构，无包目录）。
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
