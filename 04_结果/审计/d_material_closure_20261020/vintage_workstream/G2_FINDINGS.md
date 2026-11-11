# G2：EIA-860M 历史内容保管链核查

审查日期：2026-10-20，Asia/Shanghai。仅读取官方说明、公共源码、Zenodo 记录/文件元数据和 datapackage.json；未取得或读取任何工作簿、ZIP 成员、Parquet 或机组运行行。没有实验、远端作业或论文修改。

## 裁决

**两种门必须分开：**

1. **2015-07 起每个月的 EIA 首次发布原版，以及报告月末 as-of：未闭合，不可继续承诺。** 当前月名不能保证初版；EIA 的 2025-02-06 更正已经证明存在重发。PUDL report_date 也不提供首次公开字节证明。
2. **按独立托管版本的保守可知时点定义 origin：在元数据层已闭合一条有限、具体的合法路径。** Zenodo 不是只有今天的一个 DOI；原始 860M 版本族有 50 个独立版本，从 2020-11 到 2026-09。抽查 17 个版本的 manifest 与 file metadata，获得公开记录、文件身份、MD5、大小、file version_id、created/updated 和所含月份声明。没有声称读取验证其内部工作簿内容。

因此，**G2 不应被写成“没有历史档案，必须放弃 D”。** 如 D 的 G1/G3 通过，可以基于下述托管 origin 继续有限历史研究；不可借本结果恢复“2015 起完整首次发布信息集”或宣称统计样本量足够。D 的最终投资决定仍须同时满足另两门；G2 本身是有限通过。

## 核查文件与来源

- `version_index.csv`：全部 50 个版本的服务器 created、modified、声明 publication_date、公开状态及资源数。
- `selected_manifests.csv`：17 个代表版本及 manifest 声明的月份覆盖。
- `resource_identity_metadata.csv`：各代表版本资源的 MD5、大小、file version_id 与服务器时间。
- `metadata/`：本次读取的原始 JSON 元数据响应及 JSON manifest。**不含数据文件内容。**
- `collect_metadata.ps1`：仅允许 Zenodo record/version/file-metadata/datapackage JSON 路径，不请求任何数据资源内容。

公共入口：[版本族 API](https://zenodo.org/api/records/18823089/versions?size=25)、[第二页](https://zenodo.org/api/records/18823089/versions?page=2&size=25&sort=version)、[EIA 档案](https://www.eia.gov/electricity/data/eia860m/)。概念记录为 `4281336`，不是用当前最新 DOI 追认为旧时期。

## 保守 origin 规则和代表记录

`metadata.publication_date` 是描述性日期，不能独立使用。版本记录的服务器 created/modified 与各所用资源的 file created/updated 取最大值，且要求记录当前为 published/open；origin 放在该 UTC 日期之后（下表取次日 00:00 UTC）。将 record modified 也纳入，可保守覆盖公开状态/元数据的后续变化，不猜测每次修改原因。这样不需要假定 EIA 原始发布时间，也不需要将文件上标的报告月当作公开时点。

旧版 2020—2023 文件有共同集中于 2023-08-28 的 updated 时间；这与托管平台迁移/元数据变动相容，但本次没有取得足够直接记录证明它仅是迁移。因此不把旧 created 日期单独用作严格历史起点；以 updated 为保守上界。后续版本抽查的 file created/updated 与 record created 同日，能直接绑定较新的托管起点。

|版本 / 记录|服务器记录 created（UTC）|manifest 最晚报告月|保守 origin（UTC）|说明|
|---|---|---|---|---|
|v11 / [8188017](https://zenodo.org/records/8188017)|2023-07-26 23:33:08|2023-06|2023-08-29|采用 file updated=2023-08-28，而非回填7月或6月|
|v14 / [10423813](https://zenodo.org/records/10423813)|2023-12-22 12:37:52|2023-11|2023-12-23|文件更新与创建同日|
|v16 / [10611141](https://zenodo.org/records/10611141)|2024-03-01 16:54:18|2024-01|2024-03-02|文件更新与创建同日|
|v22 / [12100771](https://zenodo.org/records/12100771)|2024-07-01 16:16:07|2024-05|2024-07-02|文件更新与创建同日|
|v25 / [13866221](https://zenodo.org/records/13866221)|2024-10-01 13:48:07|2024-08|2024-10-02|文件更新与创建同日|
|v29 / [14745197](https://zenodo.org/records/14745197)|2025-01-31 23:01:11|2024-12|2025-02-01|早于EIA更正；保留旧年度包身份|
|v34 / [15516497](https://zenodo.org/records/15516497)|2025-05-26 15:59:52|2025-04|2025-05-27|不能称4月底公众已知|
|v38 / [17200983](https://zenodo.org/records/17200983)|2025-09-25 16:01:23|2025-08|2025-09-26|12个月结果在当前时点可能尚未成熟|

另核查 v43 / 18823089，服务器创建2026-03-02，描述性发布日期2026-03-01，最新月2026-01；这直接说明元数据 publication_date 与服务器创建不必同日，不能取较早者。当前公开最新报告月为2026-08，最近 origin 的6/12月标签不得推定已成熟。

上表仅证明具体归档起点与内容身份可以绑定，不证明所有月度版本都足够新鲜或有足够独立建设周期。50个版本不等于50个独立样本；同内容、近邻发布日期、重叠期限都必须保留相关性。

## 2024年12月更正反例：旧包确实有保留路径

[EIA 官方更正](https://www.eia.gov/electricity/data/eia860m/correction.php)写明：2024-12详细文件于2025-02-06重发，涉及2025计划容量。

本次只读元数据确认：

|版本|文件|字节数|MD5|file updated UTC|
|---|---|---:|---|---|
|v29 / 14745197|eia860m-2024.zip|127312249|e035585d8660c86f6a119bd26a022613|2025-01-31T23:01:11.704889Z|
|v30 / 14842914|eia860m-2024.zip|127335369|55592d39081c290b755b36f78e123be2|2025-02-10T22:04:18.173520Z|

两份 manifest 都声明涵盖2024-01至2024-12，API checksum与manifest hash相符。这证明更正前后有不同的保留年度包；没有读取内部文件，所以**尚未逐个工作簿证明差异仅来自12月、更未确认受影响项目行**。但对2025-02-01起点，使用v29这个当时已存在的固定包是具体可行的设计，不必使用今天EIA的改写文件。v30的record modified另为2025-03-03；按本次最保守规则，它作为公开输入的origin应推至2025-03-04，而不是仅凭文件时间放在2月11日。v29不存在这一额外推迟。

## 保管链强度与例外

Zenodo 的普通版本机制是创建新记录/DOI保存新文件；官方同时说明已发布文件有受控修改例外，现行30日内也存在修改机制。因此不宣称“一个DOI永远不可变”。这里同时记录文件级 version_id/checksum/created/updated；如未来发现文件级 updated 晚于某origin，该资源从该origin的合格输入中退出，而不是以publication_date倒填。

[Zenodo记录/版本说明](https://help.zenodo.org/docs/deposit/about-records/)、[记录修改说明](https://help.zenodo.org/docs/deposit/manage-records/)、[FAQ修改例外](https://support.zenodo.org/help/en-gb/1-upload-deposit/64-can-i-edit-records-after-they-have-been-published)。

独立工作流佐证：[PUDL archive issue1037](https://github.com/catalyst-cooperative/pudl-archiver/issues/1037)创建2026-03-01，记录v43发布和2026数据包CREATE。当前归档源码（blob `ec01dbe6eb121260c22643130a2351b11545c1ee`）从EIA页面采集各月链接、按年存入ZIP并在manifest登记year_month；只读源码，不运行。它说明最新归档会重新取得当时可见文件，故最新版本不能取代过去版本。

Internet Archive CDX仅尝试了元数据查询（timestamp/original/mimetype/statuscode/digest），20秒超时，未取得结果。这不是无快照或全球无档案的证据。本轮没有继续扩大搜索范围。

## 时间、实体与结果边界

须保留：报告月末状态、报送日期、公开/托管日期、修订日期、报告的商运/退役日期、首次在研究档案看见状态六种时间。当前填报规则为月末状态、次月约15日填报；不能视为当日公众获知。

官方空白表单与说明确认 Plant ID、Generator ID、状态与计划/实际日期语义；OP为商运，TS为建设完成未商运，CN/IP为取消/无限推迟。机组拆分、改名、重编号、扩容和部分投运未在本轮逐行检查，不能凭单一ID自动保证同一物理项目。建设规划阶段还允许combined-cycle总机组代码而具体机组未确定。部分投运只能按有证据的子机组/容量状态核算，不能臆造比例。

[官方表单](https://www.eia.gov/survey/form/eia_860m/form.pdf)、[填报说明](https://www.eia.gov/survey/form/eia_860m/instructions.pdf)、[EIA档案说明](https://www.eia.gov/electricity/data/eia860m/)。

字段级实体/结果规则具有明确来源，实际覆盖仍是另行授权后的数据资格工作。只需证明reported-in-service组合时，不应把缺少实物现场认证升级为数据源不存在；同时不得把登记容量写成可调度容量、容量信用或实际供电充分性。

## 投资意见

**就G2作决定：允许继续“固定托管origin的有限历史研究”路线，不建议因版本材料放弃D；拒绝原先暗含的完整2015起首次发布回测。** 这不是给实验放行，亦不能盖过G1的近邻贡献问题或G3真实行动链的失败。如果D最终停止，准确理由应是其他关口或有限历史研究不满足目标贡献，而不是“EIA没有可保留的历史内容”。
