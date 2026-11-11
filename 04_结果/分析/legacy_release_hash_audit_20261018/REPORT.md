# 旧发布包成员哈希核对与文档勘误

日期：2026-10-18。范围：本地旧 ZIP、现存隔离克隆、历史 Git 清单与源码。E07 保持未激活；未运行校准、模型推理、重打包、下载或发布。

## 核实结论

**VERIFIED：两处成员身份差异已定位为文档记载不一致。** 当前旧包的外层 SHA256、两成员的完整 SHA256 与大小，均与发布标签 `tste-submission-v1.0`（`1085f23c925b7b9bfc312608cbaaecc50cba676e`）的清单一致；本地散文件及现存 `E:\windfarm_reproduction_final` 中的包和散文件也一致。没有发现需要替换发布成员的依据。这里证明的是现存字节与历史清单相符，不能证明从发布以来从未发生任何文件操作。

| 成员 | 字节数 | 实测 SHA256 |
| :--- | ---: | :--- |
| `artifacts/fixed_forecast_residuals.npz` | 173410167 | `b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9` |
| `artifacts/matched_budget/cached_posterior_probs.npz` | 22475033 | `d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca` |

外层 ZIP：195613174 字节，SHA256 `cf90924b1fead36317addabfcbee6aa6236bebc29889f8ce5dfd57466fc7fc22`。ZIP 恰含上述两个成员，无重复名称。逐成员流式读取并计算完整 SHA256，未向原目录解包。

## 历史版本定位

1. `2c71ffc2`（2026-09-25）首次引入的产物清单已记录上述正确成员哈希和大小。`b8d894e5` 的文本换行归一化、发布标签 `1085f23c`、随后 `a273a05b` 的清单中，这两成员身份不变。
2. `docs/EXTERNAL_RELEASE_METADATA.md` 在首次提交 `1085f23c` 就包含两个错误全哈希，大小正确。残差旧值为 `b05b3751f45e2a2c1619623da3d038317769caec7d6a59b207eb4ea088e5d0d7`，后验旧值为 `d40f0ddbaee7452d3a339dd8917e766fb31ec227242c7f078d46a48970e4e7e7`。
3. `docs/EXTERNAL_REPRODUCIBILITY_VERDICT.md` 在首次提交 `a273a05b` 就包含另一组错误全哈希：`b05b3751f45ecb37119ff9574d75d50ae9ba19028f8f2b7405cb70d691e8eaec`、`d40f0ddbaee7a04a3952ba5c7c0018f45037d0c0082f6f3eb17ffc0c800ea65d`；后验大小还误写为 22572551 字节。本次连同大小一起勘误。
4. 两份文档的错误值分别保留了正确哈希的前 12 位。**INFERRED：这更符合文档全值填录错误，而非现存 ZIP 成员被换版。UNKNOWN：错误后缀如何产生，尚无原始编辑过程记录，不能断言为某种具体手误或动机。**
5. 现存隔离克隆 HEAD 为发布标签提交，其包与成员再次核对一致。这只是当前文件观察，不能独立追认旧报告关于历史隔离环境、下载执行及全部 19 项主张的叙述。未重新访问公共下载端点。

完整历史文件快照、Git blob、提交和 SHA256 见 [historical_versions.json](historical_versions.json)。勘误前工作树原文的逐字节快照见 [snapshots/](snapshots/)，并由 [新成员清单](release_members_corrected_manifest.json) 绑定。旧 E07 可用性审计中的“不一致待追查”记录及其旧输入哈希均保留；本报告是后续补充，不覆盖旧观察。

## 生成版本核对及未闭合边界

**残差文件：** 原发布文档写 `scripts/decisive_fair_risk_benchmark.py`，发布标签清单却写 `scripts/run_fixed_target_contract.py`；后者在发布标签中不存在。标签内确有 `scripts/build_fixed_forecast_residuals.py`，源码直接写出相同路径与元数据，定义 201—205 五种子及六个 horizon；其标签版 SHA256 为 `a5bc5888e59850fda9cdc910a0d8cafb45249f42f8f4d42de4d9bc15a35f065d`。`00c92f0b`（2026-10-15）已将清单/清单生成器中的路径改为该脚本，成员哈希与大小没有变化。本次只将发布文档改为“源码相容的生产者归属”，并明确实际执行版本 UNKNOWN，不追改历史清单。

**后验文件：** 历史清单与发布标签源码均指向 `scripts/run_matched_budget_frontier.py`，源码存在后验缓存读写分支；标签源码 SHA256 为 `5c809aec0c0d3e91d8dfa6f1ac6c506458edddd718d439d81630289843e3e31f`。但原 `provenance.json` 记录的 HEAD 是 `621bb8b5817483f54bfb7a51fcd0f9a0751fc542`，时间戳为 `2026-09-22T01:51:21.430134+00:00`，该提交中不存在此脚本路径。因此这个 HEAD 不能绑定当时可能存在的未提交源码；源码存在缓存复用分支，也使 campaign provenance 不能独立证明缓存首次生成的执行版本。

**打包：** 版本化 `package_release_artifacts.py` 选择 Category B 并逐文件核验清单 SHA256；旧证据账本记录执行该命令成功，外层 `.sha256` 与本次实测相符。这些记录支持包的身份与既定打包方式，但未发现绑定实际执行源码、运行环境和成员哈希的完整原生成凭证。ZIP 成员时间戳仅作不可信元数据留档，不作为生成时间或源码版本的证明。

版本化源码定位、存在性与相关行见 [source_versions.json](source_versions.json)，原 campaign provenance 与原证据账本亦已快照。**生成链完整闭合状态：UNKNOWN / NOT CLOSED。** 本次没有通过重新生成来补写历史事实。

## Claim–Evidence 对照

| 主张 | 直接证据 | 状态与边界 |
| :--- | :--- | :--- |
| 两成员的大小和完整哈希与历史清单相符 | ZIP 流式实测、初始/标签清单、两处现存散文件 | VERIFIED，限文件身份 |
| 文档错误在各自首次提交已出现 | 首次提交文档快照和同提交清单 | VERIFIED，不推断编辑动机 |
| 正确生产源码可精确追溯到实际执行版本 | 路径矛盾、缺少版本绑定生成凭证、后验 provenance HEAD 缺脚本 | UNKNOWN，不能以标签源码替代执行快照 |
| 成员身份一致即可重新认证全部科学主张 | 无本轮主张重放或独立科学审查 | 不支持；旧 verdict 仅保留为历史记录 |
| 此包可激活 E07 | 旧坐标审计及 E07 空绑定保持不变 | 不支持；E07 继续未激活 |

可用于文稿的有界表述：

> The unchanged legacy release archive contains two members whose full SHA256 digests and byte sizes agree with the release-tag artifact manifest. The conflicting documentation has been corrected with the original records preserved. This establishes file identity, while the exact original generation execution remains unverified and no scientific certification is upgraded.

## 本次变更与验证

只修正两份发布文档的成员元数据和来源表述，新增版本化勘误清单、证据快照及本报告；历史清单、ZIP、散文件、原始实验结果和 E07 协议保持原样。旧文档关于 19/19 的文字在 verdict 中作为历史记录保留，并加上本次不续证的醒目标记。

保护清单见 [protected_inputs_before.json](protected_inputs_before.json)；复核记录见 [verification.json](verification.json)。验证只包含文档/身份检查及既有门禁，不运行 `fetch_artifacts.py`、打包脚本或实验生产脚本。既有科学与数字门禁的通过只覆盖它们编码的检查，不能补齐上述原生成凭证缺口。

验证结果：16 个受保护文件的前后大小和完整 SHA256 均一致；包成员/历史清单/勘误文档精确匹配，原文快照哈希及文档本地链接通过检查。E07 三项激活绑定及确认性数据清单仍为空，合格窗口计数仍为 0。既有 E07 数据盘点测试 **8 passed**；科学主张门禁与数字一致性门禁均通过。没有改动生产代码或门禁规则。
