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
