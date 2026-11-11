# MLWA全文续查：仅新增路径

日期：2026-10-20。对象：Kandemir等，*Machine Learning with Applications* 25 (2026), 100957，DOI [10.1016/j.mlwa.2026.100957](https://doi.org/10.1016/j.mlwa.2026.100957)。

本文件追加到新目录；不修改上一轮13入口、旧判断、主问题或论文。延续已读research-skill和科学契约，本轮复读AGENTS及最新PROJECT边界。没有测量数据获取、实验、推理、远端计算、联系作者或登录。

## 1. 本轮结论

**完整PDF/完整HTML仍未取得；全文门不升级。** 但本轮得到三项可核进展：

1. 查明NVA真实公开API和内容协商要求，成功取得论文JSON，确认该条目的公开附件列表为空。
2. 成功取得正确OpenAlex记录，得到实际列出的OA PDF和OpenAlex全文副本地址；前者403，后者401，均停止，未绕过。
3. 出版社公开索引新增§2.2/2.4细节，已能明确作者的一分钟前瞻任务、单步输入和列明七个输入不含当前P。它们仍是部分正文证据，不拼作全文。

**论文页数、完整正文SHA256仍UNKNOWN/NOT_OBTAINED。** 新存档的JSON和网站声明文件只用于访问路径和元数据核验，不是论文全文。

## 2. NVA：不是已证API迁移，而是缺失Accept头

从[NVA论文公开HTML](https://nva.sikt.no/registration/01a014031ebd-f999b58e-d400-4951-8306-979b270587b1)实际声明的脚本读取配置，未执行远程JavaScript：

- `constants-CIOl1lOJ.js` 声明baseURL为 `https://api.nva.unit.no`。
- `apiRequest-CipB3k1F.js` 给公开请求设置 `Accept: application/json`，并声明 `Registration=/publication`。
- `registrationApi-DWhx4LSM.js` 明确未登录分支使用公开GET获取 `/publication/{identifier}`。
- `useFetchRegistration-DZ3phq_Z.js` 说明该函数用于加载登记记录。

按网站本身公开声明、无凭据请求[实际API](https://api.nva.unit.no/publication/01a014031ebd-f999b58e-d400-4951-8306-979b270587b1)，本轮得到HTTP200、`application/json`，响应10776字节。

**VERIFIED（该公开记录）：** `status=PUBLISHED`、`associatedArtifacts=[]`、`pendingOpenFileCount=0`；`entityDescription.publicationDate=2026-07-16`；Handle仍为11250/5558015。上一轮HTML应用壳不能归为已证接口失效/迁移，本轮按明确内容协商闭合。空附件只覆盖这一条公开登记，不能扩大成作者或全机构绝无副本。

## 3. OpenAlex新路径：真实链接，无猜测路径

请求[OpenAlex DOI记录](https://api.openalex.org/works/https://doi.org/10.1016/j.mlwa.2026.100957)时明确接受JSON，取得work `W7169855474`。首次PowerShell默认JSON解析因摘要词键大小写冲突失败，随后使用保留大小写的hashtable解析；原JSON不是无记录。此错误与修复均保留。

记录中：

- `open_access.oa_status=gold`，`any_repository_has_fulltext=false`；后者仅为OpenAlex收录范围。
- 实际 `pdf_url` 为 [ScienceDirect论文PDF](https://www.sciencedirect.com/science/article/pii/S2666827026001222/pdf)。对这个首次由权威发现记录给出的具体地址只作一次普通访问，返回403；未构造其他PDF路径或查询变体。
- 实际 `content_urls.pdf` 为 [OpenAlex所列PDF副本](https://content.openalex.org/works/W7169855474.pdf)。匿名HEAD返回401，停止；没有寻找凭据、注册账户或改变安全配置。
- 另有DOAJ记录链接，但无PDF地址；该目录页工具访问失败，没有发现新全文位置。

不再重复上一轮出版社挑战页、DOI跳转、作者主页或旧Handle访问。没有使用Unpaywall的邮件参数代填任何真实用户或作者信息；本轮已有的OpenAlex公开定位未提供可匿名取得的副本。

## 4. 本轮新增原文证据及其上限

来源仍为[出版社公开索引正文](https://doi.org/10.1016/j.mlwa.2026.100957)，不是完整HTML文件。

### 时标声明已闭合，实施验证未闭合

§2.2明确写为 `P_hat_t=f(x_(t−1))`：前一分钟变量预测下一分钟功率，刻意只使用一个历史时点，以便解释扰动；更长滞后不纳入。**不得把这篇文章贬为同期功率曲线估计，也不得说它没有任何前瞻状态预测。** 这确认作者的任务声明，不能替代其代码、数据和全处理链核验。

### 输入和样本范围得到进一步限定

§2.4列出Zephyros 2.3MW单机、SINTEF数据、1分钟重采样、约两个月87600条清洗记录、60/20/20时序切分。active power为目标；七输入是风速、齿轮箱油温、轴承温度、RPM、yaw、blade angle、环境温度，**列明输入不含当前P**。原文还说明剔除异常、负功率及停机/限电样本，文末标记数据保密。

这些新增证据支持将可能差异收窄为“在强当前功率及更完整历史之后的状态增量”，而非“别人只做同期关系”。**不能据此断言完整文章没有其他P-only消融、决策附加试验或补充分析；这些仍未全文核清。** 也不能用其已清洗的正常运行样本论证本项目包含停机/限电的所有短缺总体。

## 5. 对整合结论的影响

本轮修正了两个访问/阅读未知：NVA公开附件确为空；作者一分钟前瞻和所列输入已明确。没有改变完整正文未取得这一事实，不能把新颖性排重标为完成。

该文足以排除“首次状态前瞻预测”“首次控制区间解释不确定性”等宽泛创新口径。对当前主问题更精确的比较——完整后果历史I对(I,Z)、固定目标和共同可行动作的配对损失——仍只能登记为拟议差异，不能作全文排他性结论。

本支到此结束新增路径查阅；不以继续检索维持HOLD，不启动实验，不请求作者材料，不恢复TSTE投入。是否停止当前机制承诺，应继续由已完成的项目识别审查决定，而不是把网页拒绝访问当科学证伪。

## 6. 记录文件

- `SOURCE_MATRIX.csv`：只列本轮新增路径和响应。
- `nva_publication.json`：Accept协商后获得的公开记录。
- `openalex_work.json`：正确work元数据，保留原大小写词键。
- `public_endpoint_provenance.json`：公开脚本URL、相关声明及获取记录；没有执行其中任何代码。
- `artifact_hashes.json`：上述本地证据文件大小与SHA256；**不含论文全文哈希**。

新增文件只作静态格式核验。旧审查、论文、科学契约、模型、原结果及运行队列未改。
