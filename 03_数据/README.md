# 数据

| 位置 | 内容 |
| --- | --- |
| `原始/wtbdata_245days.csv` | 原始 WTB SCADA，保持原字节 |
| `原始/sdwpf_baidukddcup2022_turb_location.CSV` | 机组位置 |
| `外部数据` | 已有外部风场资料，保留下载与来源目录结构 |
| `派生缓存` | 已生成的特征、数据分割和其他缓存；旧 `artifacts/cache*` 由路径解析器定位 |

本目录为本地资产，已加入 `.gitignore`，不会随代码提交。模型权重、日块结果、冻结动作等与实验身份绑定的材料仍随对应实验结果包保存在 `04_结果`，避免拆散收据与输入关系。

查看实际位置：

```powershell
python project.py locate wtbdata_245days.csv
python project.py locate artifacts/cache_signature
python project.py locate data/external_wind
```

旧协议可能绑定 Metis Lustre 上的完整年份包、冻结权重及环境。本地目录有可见结果不表示这些远端输入已全部下载；不自动替换缺失文件，也不在此次整理中联网采数。
