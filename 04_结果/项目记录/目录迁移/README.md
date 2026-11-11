# 路径映射

`path_map.json` 将历史逻辑路径和迁移前物理路径直接映射到现存位置。最长匹配前缀优先；逐层拼接与直接读取同一历史路径得到相同位置，包括落在数据目录的 `artifacts/cache*` 例外。

```powershell
python project.py locate experiments/E04
python project.py locate analyses/praw_supplement_v3_execution_20261021
python project.py locate artifacts/cache_signature
```

原有身份清单、冻结结果和 manifest 中的旧路径不改写。2026-11-11 按用途重构后的目录是 `01_当前论文`、`02_代码`、`03_数据`、`04_结果`；没有尝试/阶段层级。迁移清单、原映射备份和验证见 [目录重构记录](../复现目录重构_20261111/README.md)。上一轮删旧版的记录在 [文件清理记录](../文件清理_20261111/README.md)。
