# 共用工程

推荐从项目根目录使用 `python project.py`。原有科学门禁与数字门禁保持原判定：

```powershell
python project.py cli --help
python project.py scientific-gate
python project.py number-gate
python project.py run-script scripts/run_independent_confirmation.py --help
python -m pytest 02_代码/工程/tests/test_repository_paths.py -q
```

现行论文与隔离输出使用 `verify`、`reproduce-results`、`redraw`、`build-paper`，详见 [复现说明](../../复现说明.md)。`--root-dir` 仍指整个项目根目录；Python 包名与科学算法保持，旧协议输入通过 `repo_paths` 定位。

## GitHub Actions

自动任务从不含原始数据/权重的发布检出运行：源码编译、`verify_github_checkout.py`、冻结科学/数字门禁与合成数据单元测试。发布检查接受真实的已封存状态，但不把它修改为已完成，也不调用历史任务完成门禁。

`workflow_dispatch` 默认只运行上述检查。选择 `full_gate` 需要带 `research-data` 标签的自托管 runner，以及仓库变量 `REPRODUCTION_WORKSPACE`；该目录必须已准备完整冻结材料，且 HEAD 与本次运行提交相同。完整检查写入 runner 临时目录，不下载、上传或重生成原始数据/权重，不触发训练。
