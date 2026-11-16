# 质量门禁（quality-gates 分支）

本文件由 `quality-gates` 分支新增，说明这套门禁怎么用、每道门禁拦什么，
并附首次运行报告摘要。本分支**没有改动任何业务代码**（`inject_tool.py`、
`zcode_sync.py`、`watch_agent.py`、`watch_reinstall.py`、`run.py`、
`zcode-model-puller.js`、`install.sh`、`uninstall.sh` 一行未改），全部是新增文件。

## 一条命令

```bash
pip install -r requirements-dev.txt   # 首次使用时装门禁工具
python tools/run_quality_gates.py     # 或：make check
```

依次执行五步，任一步失败立即停下、打印原因并以非零码退出，全过才算通过：

| 步骤 | 内容 | 拦截条件 |
| --- | --- | --- |
| 构建检查 | `python -m compileall` 全部 .py；`node --check zcode-model-puller.js`；`bash -n install.sh uninstall.sh` | 任一语法/编译失败（无 node 时 JS 检查标注跳过，不算失败） |
| 测试+覆盖率 | pytest 跑 `tests/` 冒烟与纯函数测试，pytest-cov 量 5 个业务模块覆盖率 | 有测试失败，或总覆盖率低于门槛 |
| 依赖门禁 | pip-audit 审计 `requirements-dev.txt` | 发现已知漏洞 |
| lint 门禁 | ruff 硬门禁规则集 F（pyflakes）+ E9（语法类） | 有硬门禁问题（存量基线除外，见下） |
| 部署检查 | 静态校验 install/uninstall 引用的文件都存在 + 临时目录模拟安装布局 | 引用文件缺失 |

CI：`.github/workflows/quality-gates.yml` 在 push / PR 时跑同一条命令。

## 门槛与取舍（为什么是这样）

- **覆盖率门槛 27%（ratchet 基线）**：仓库此前没有任何测试，覆盖率从 0 起步。
  首跑实测总覆盖率 27.32%，门槛取实测值向下取整 = 27%，写在
  `pyproject.toml` 的 `[tool.quality_gates] coverage_min`。含义是“不许退步”：
  以后新增代码若拉低总覆盖率就会被拦；提高门槛时同步改这个数，只升不降。
  测试只测可离线验证的内容（模块导入/编译、纯函数、脚本引用文件存在性），
  不为了凑覆盖率去改业务代码或硬测依赖 ZCode 环境的逻辑。
- **lint 只硬拦 F + E9**：这两类是会真正导致运行错误的问题（未定义名、
  未使用导入、语法错误）。行长（E501）、文件末尾空行（W292）等风格问题
  以 `--exit-zero` 方式只报告不拦截——先把“对错”管住，不一上来用“风格”堵门。
- **lint 存量基线**：首跑发现 3 处既有 F401 未使用导入（`run.py` 的 `os`、
  `Path`，`zcode_sync.py` 的 `sys`）。本次落地约束是不动业务代码，故在
  `pyproject.toml` 里用 per-file-ignores 只对这两个文件豁免 F401，
  并列入下方修复项；其余文件（含新增 tests/、tools/）的 F401 仍是硬门禁。
- **依赖范围**：业务代码全部是 Python 标准库（os/sys/json/re/urllib/
  plistlib/struct/subprocess/hashlib/fcntl 等），无第三方运行时依赖，
  因此没有、也不需要 requirements.txt。`requirements-dev.txt` 只固定门禁
  工具本身的版本，并接受 pip-audit 审计。
- **部署检查不执行真实安装**：install.sh 会调用 inject_tool.py 改动本机
  ZCode 应用目录且依赖 ZCode 本体与 npx，属于真实安装动作。门禁只做
  静态校验（脚本语法、引用文件存在）与临时目录模拟布局。

## 首次运行报告（摘要，2026-11-16）

环境：Python 3.12.3、Node v24.22.1、pytest 9.2.0、pytest-cov 7.1.0、
coverage 7.17.3、ruff 0.17.5、pip-audit 2.10.1。结果：**五步全部通过**。

- 构建检查：通过。全部 .py 可编译，JS 与两个 shell 脚本语法正确。
- 测试+覆盖率：通过。23 个测试全部通过；总覆盖率 27.32%（门槛 27%）。
  分模块：inject_tool 25%、run 13%、watch_agent 39%、watch_reinstall 28%、
  zcode_sync 29%（语句覆盖率）。
- 依赖门禁：通过。pip-audit 审计 requirements-dev.txt（5 个工具包），
  未发现已知漏洞。
- lint 门禁：通过。硬门禁 F+E9 无问题（3 处存量 F401 已基线豁免，见上）；
  报告-only（E,W）共 10 处：E501 行过长 6 处、W292 文件末尾无空行 3 处、
  W293 空行含空白 1 处，均不拦截。
- 部署检查：通过。install.sh / uninstall.sh 共引用 2 个文件
  （inject_tool.py、watch_agent.py），均存在；临时目录模拟布局完整。

搭建过程中的真实记录（不美化）：首轮试跑时测试全过之前先暴露了两个问题——
一是新写的测试辅助函数构造 asar 头部时少补了 4 字节（测试自身 bug，已修，
业务代码无误）；二是 lint 查出上述 3 处存量 F401。两者处理方式如上。

## 待修复项（需要批准改业务代码后处理）

1. 删除 3 处未使用导入：`run.py:8 import os`、`run.py:9 from pathlib import Path`、
   `zcode_sync.py:11 import sys`；删完后同步移除 pyproject.toml 的 per-file-ignores 基线。
2. （可选，不拦截）报告-only 的 10 处风格问题：E501×6、W292×3、W293×1。
3. 覆盖率短板在 run.py（13%）：其逻辑以交互式 CLI 为主，后续可把可离线
   的分支逻辑拆出再补测试，并相应上调 coverage_min。

## 合入方案

- 分支：`quality-gates`（计划从 main @ 6a287c5 建）。注：2026-11-16 首次推送时
  GitHub 返回 403（Muse 的 GitHub App 对本仓库无写权限），远端分支尚未建成，
  本地成品完整保留；给 App 开通 Contents 读写权限（或手动建好同名分支）后即可推送。
- 推送成功后同样是**未建 PR、未合入**，等确认。
- 合入步骤：确认后在 GitHub 上从 quality-gates 向 main 发起 PR，CI
  （quality-gates.yml）跑绿后合并即可；本分支只新增文件，与 main 无冲突面。
