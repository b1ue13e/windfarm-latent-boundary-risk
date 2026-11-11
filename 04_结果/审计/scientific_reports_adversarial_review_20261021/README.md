# Scientific Reports 投稿前对抗审查（不修改稿件）

当前结论：保留固定受控比较实证主线，建议大修后再考虑投稿。不把影响力、独立年份或现场经济收益作为该刊统一硬门。新核定的R早期state-fit名义publication例外须按报告SR-08准确披露并收窄；若坚持全阶段无例外发布模拟，则需要另授权纠正，不能靠措辞修复。

- `REVIEW.md`：完整报告、四问判定、pinball成本恒等式、近邻差异、逐图证据、负结果解释、投稿前验收。
- `ISSUES.csv`：8项建议，S3六项、S2两项；均注明证据、权威、位置、验收和是否需要新实验。
- `CLAIM_EVIDENCE_DISPLAY_REVIEW.csv`：13项主张—原文件字段—图表—判断—边界。
- `STORED_FAILURE_WITNESSES.csv`：44行既存风险/严重度界定位；没有新置信界。
- `WEB_SOURCE_SCOPE.json`：官方审稿/投稿标准及近邻实际阅读范围；SETA/SAFER最终全文仍未取得。
- `REVIEW_SOURCE_CHECKS.json`：51项只读核对；不是区间覆盖、独立外审或录用认证。
- `CLOCK_BOUNDARY_AUDIT.json`：由原训练索引/源码定位的历史state-fit时钟例外；没有重跑或估算修正效应。
- `PRESERVATION_BEFORE.json`：当前稿、V2、契约等358个文件的审查前字节身份；审查末再次比较。
- `legacy_claim_gate.txt`、`cached_numbers/`：原科学门禁与77项缓存数字检查，限其旧职责。
- `render/`：本轮从当前PDF重新生成的22页及联系页，本地保留、Git忽略；当前正文13页、补充9页。旧稿目录内旧联系页不用于替代当前渲染。

只读核查复跑：`python -X utf8 -B research_audit/scientific_reports_adversarial_review_20261021/audit_review.py`。只写本审查目录，读取已保存聚合结果和文件身份，不执行任何实验实现。旧稿的 `validate_release.py`会写旧稿QA，因此本轮没有直接调用它；其92项既有记录与未改候选字节相绑定。

本轮没有修改论文、图、结果、阈值、V2、PROJECT或科学契约，没有训练、推理、校准、重采样、测量下载、远端访问、公开上传或投稿。稿件作者批准与材料发布另待落实。
