# V2 可复核包独立核验

**裁决：`PASS_PORTABLE_ARCHIVED_RESULT_REVIEW_WITH_OPEN_PUBLICATION_RESPONSIBILITIES`。** V2 ZIP 已具备脱离原仓库核对既存统计、主要判定和图3字段的实际能力，WE-07 的技术整理部分已实质解决。公开存档、权利和作者声明仍未关闭；本结论不代表完整训练重现、统计覆盖认证或正式投稿放行。

本项只复核原审查 WE-07 及其相关证据范围，不裁定全稿新颖性或本刊编辑意义。已读 `AGENTS.md`、科学契约、PROJECT、原 REVIEW、V2 包说明及验证源码；采用学术审查技能的复核原则。本项的“独立”指重新取包、隔离执行和直接核对来源，不声称与其他角色具有独立错误过程，也不声称外部认证。

## 1. 对象、身份与隔离执行

`VERIFIED`：只读对象为 `manuscripts/wind_energy_v2/wind_energy_v2_review_package.zip`，32,877,316 字节，SHA256：

```text
6c01787351a6ffbc6bf61262593dc2a533f12c6d86c1278b838d4fecc2f95e96
```

ZIP 共71个文件成员、解压合计107,420,682字节；MANIFEST列69项载荷，另两项是MANIFEST自身及旧PORTABILITY_CHECK报告。MANIFEST SHA256为 `edf1e7760eb3a9904203dcb0801019f5cd536e2acc8c0ddfcedc2d9df0e704e4`。逐成员检查无绝对路径、`..`、反斜杠/盘符逃逸、重复名、符号链接或加密项，随后只解到新建的仓库外临时目录；临时目录保留，本文不披露个人路径。

在仓库外实际执行，Python为3.12.10：

| 执行 | 实际结果 | 含义 |
|:--|:--|:--|
| `python -I -S -B <external-package>/verify_package.py` | exit0；`PASS_ARCHIVED_RECORD_AUDIT`；69项载荷SHA通过 | 隔离模式、禁site、禁字节码写入后仍能核对既存记录 |
| 在外部包目录执行 `python -S -B -m unittest test_package.py -v` | exit0；8/8通过 | 包内回归测试可脱离项目安装运行 |
| `python -I -S -B <external-package>/refresh_manifest.py --check` | exit0；`PASS_MANIFEST_CHECK` | 只检查白名单与原manifest，未刷新manifest |
| 对同一verifier追加Python审计钩子后执行 | `PASS_GUARDED_OFFLINE_EXECUTION` | 禁止网络/子进程事件；未发生相关事件，无仓库/第三方包外部读取依赖，无`source_static`执行 |

审计钩子记录的文件访问限定于外部包与Python标准库安装；未发现site-packages模块。verifier及manifest检查器的导入均为标准库，测试只额外导入包内两个验证模块。`source_static`会被读取以计算hash，但未被导入或执行。没有模型、测量文件、私人skill、原仓库安装或网络才能通过的隐含路径。

## 2. 包与V2、原来源是否相符

`VERIFIED`：独立使用ZIP字节，而非旧PORTABILITY_CHECK的PASS字样，核对以下身份：

- 71个解压文件逐字节等于ZIP；71个ZIP文件均与当前本地包目录对应文件相同；ZIP成员集合严格等于69项manifest白名单加上述两项，未夹带额外文件。
- 与V2根目录核35项：正文/补充的MD、TeX、PDF，书目和CSL，四问/回应/缺口/接口文档，12个四图导出、4个V2源CSV及图3字段manifest、6个补充CSV，全部字节相同。接口文档在包中改名为`documents/INTERFACE_EVIDENCE.md`，与根目录`interface_review/INTERFACE_AND_NEIGHBOR_REVIEW.md`相同。
- PROVENANCE的50项原仓库来源全部存在，当前原文件hash与声明的original hash相符；包文件与package hash相符。标为BYTE_IDENTICAL的文件确实相同。
- protocol投影仅删声明的两个内部root字段；freeze投影仅删内部绝对路径键的historical_manifests；seed账本只删host列，其余单元格相同。unlock投影的事件除pbs_job外与原事件相同，有限目标数和原收据hash保留；该投影并非完整原收据。
- 8份静态源码与所记Git commit内容在CRLF归一后相符。7份声明与confirmation freeze的源码hash相符；`run_information_subset_study.py`明确记录`freeze_source_hash_match=false`，未将其冒称该freeze成员。不能把这些片段称作已安装或齐备的全执行环境。

末次复查ZIP、MANIFEST、69项载荷及50项原来源hash均保持不变。完整映射和命令输出见同目录 `package_verification_evidence.json`。

## 3. 验证器是否只是自证

**不是仅散列循环。** `verify_package.py:60`与`:73`直接从既存风险/成本界重新构造可能可行、风险合格、成本充分、注册字典序最小资源及较小候选排除；随后与归档判定和CSV逐项比较。它没有生成新置信界，也不以测试PASS倒推研究真实性。

| 责任 | 实际覆盖与结果 |
|:--|:--|
| 主q=.95 | 核标签、14坐标族、2%/10%门、五fit风险上界、历史选择hash和参照标签、freeze/unlock绑定，以及图2相应字段。成本溢价+0.564147%，既存区间[+0.357468%,+0.770827%]，最大fit风险上界6.202468%。不是成本改善。 |
| Towie90格 | 对三块长、六条件、五容限重判全q充分性和最小性；得到18无充分候选、26未解决、46有限族最小。不是90次独立重复。 |
| WTB420格 | 由原aggregate界重判两分析，逐格核necessity及最小性CSV；367无充分候选、53未解决、0最小性。三日/2%的28格仍均有风险合格者但无充分候选。 |
| V2图3 | 对17行直接核原secondary_span3字段：两行成本/风险上界及资格、控制竞争者、15个排除。q=.925成本上界0.9741996%，q=.95为3.5178151%；后者是未认证，非已证真实超2%。 |
| 排除见证 | 两个风险见证确有fit风险下界大于10%；13个成本见证均要求见证策略的所有fit风险上界不超过10%，且较小候选相对该见证的成本下界超过2%。控制上界的PQ36/HGB/q=.90仅可能可行，未混写成风险合格见证。 |
| 后果账本 | 核10行、五固定seed及共同计分数，重核既存五fit均值与derived记录，U点增加2.184349%；未伪造新区间或显著性。 |

必须保留的覆盖边界：63/24/3“冻结选择”结果在本verifier中是对既存JSON状态、CSV及计数的一致性检查（`:154–168`），没有从历史/确认界完整重建这一支状态；WTB充分性CSV不是420行全部字段重新导出，而是对关键28格检查，其420格最小性分类有实质重判。图1/4和图2/3的像素并未由本包独立重绘，图2数值及图3全部决定字段被核，其他图/CSV主要由文件身份约束。这些不使当前主要复核失效，但不应将“全部附件身份通过”写成“每个附件字段均独立推导”。

MANIFEST不hash自身，旧验证输出不算科学载荷，避免了要求自含hash的结构循环。但作者若同时替换数据、verifier与manifest，散列也能再一致；本包没有第三方签名或可信时间戳。hash证明给定文件身份，源码/收据绑定支持追溯，均不能单独证明真实执行史、未看数据史、原始测量质量或名义覆盖。本次对本地原来源的直接比对加强身份核对，仍不构成上述科学认证。

## 4. 敏感内容与版权范围

`VERIFIED`：按完整成员清单，未发现`__pycache__`、pytest缓存、字节码、私人skill、Git目录、权重/数组/测量归档或notebook。PDF成员仅本稿、补充和四幅自制图；未发现第三方版权论文全文成员。包中包含书目及保留原许可的CSL，不能据此推导作者已获整个包的再分发许可。

另对71项文本/二进制解码和126个可解压PDF流扫描个人Windows路径、私人Linux路径、私人skill目录、常见GitHub/OpenAI凭据、私钥及URL内联凭据模式，无确认命中。宽Windows路径模式曾匹配PNG的一个压缩IDAT数据块；逐PNG块复查确认其为压缩字节误报，tEXt元数据不匹配。该过程未输出疑似凭据正文。模式扫描不是对所有可能编码的秘密的穷尽证明。

没有删除旧缓存，也未为“干净”而修改ZIP、manifest或图像。

## 5. WE-07剩余责任与投稿影响

| 子项 | 本次判定 | 对投稿的实际影响 |
|:--|:--|:--|
| 脱离本机的既存结果复核 | **FULLY_ADDRESSED，限定上述范围** | 不宜继续以“只有仓库相对路径/不能脱机复核”否定V2。 |
| 长期公共URL/DOI | **NOT_PUBLISHED，诚实披露** | 公开复核承诺尚未兑现；应由作者定存档方式。本文不在未核本刊初投政策时把“未有公共DOI”单独宣告为普遍初投硬门。审稿期提交可访问附件与正式公开存档是不同责任。 |
| 作者同意、权利、基金/冲突等 | **UNKNOWN/待作者确认** | 正式提交与对外发布前必须完成适用确认；本包及数值PASS无法代作者授权。ORCID的具体强制性应以投稿系统要求为准，不能虚构。 |
| 完整训练/原bootstrap重现 | **NOT_PROVIDED，未冒称完成** | 真实缺口；当前窄“既存统计与判定可复核”不能被写成全链可重现。没有证据仅凭该缺口就必须追加训练才能投稿；若要声称完整重现或期刊另有要求，必须另行闭合。 |
| 精确运行接口、实际收益、统计覆盖 | **包不建立，文稿明确保留** | 不因manifest或离线验证通过而解决。它们对应用意义/扩大主张的影响应由全稿审查另判，不能用更多hash替代。 |

正文可用性段、SI S5/S8、包README和PUBLICATION_GAPS均明确：本地待发布、无永久公共URL、权利未确认、原始测量/权重/动作/拟合索引不在包内，不能重建训练或原bootstrap。当前没有“已公开”“全训练可重现”的相互矛盾声明。整体WE-07应记 **PARTIALLY_ADDRESSED**：技术子项已关，外部发布与作者责任保留，而不是继续一概S3技术失败或提前记全部关闭。

本轮未训练、推理、校准、重采样、采新测量、访问远端、改阈值、刷新manifest、公开发布或投稿；未导入/执行`source_static`。仅新增本报告和验证JSON，仓库外独立临时材料保留；未改PROJECT、主稿、ZIP或原结果。本报告没有宣布新的实证里程碑或全范围科学认证。
