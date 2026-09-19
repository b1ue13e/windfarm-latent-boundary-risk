# Paper Consistency Checklist (学术论文一致性终检验收表)

## 核心证据链闭环核查

| 检查维度 | 核查点 | 通过判定标准 | 状态 |
|---|---|---|---|
| **问题一致性** | Title vs. Failure Sentence | 标题所承诺的研究范畴能完全覆盖第一句 Failure 场景 | [ ] |
| **缺口一致性** | Intro Gap vs. Experiments | 实验中是否单独设立针对该 Gap 的专项评测，而非仅测平均分 | [ ] |
| **假设一致性** | Hypotheses vs. Ablations | 每一条子假设均有专属的消融实验或对照组予以支撑 | [ ] |
| **方法一致性** | Math vs. Implementation | 公式中的所有损失项与超参数在开源代码中均有明确实现与配置 | [ ] |
| **数据一致性** | Claims vs. Protocol | 严格杜绝在看过 Test 结果后微调超参再宣称 Untouched Test | [ ] |
| **贡献一致性** | Contributions vs. Results | 贡献陈述未超出实验协议与数据集所能支撑的合理推广边界 | [ ] |
