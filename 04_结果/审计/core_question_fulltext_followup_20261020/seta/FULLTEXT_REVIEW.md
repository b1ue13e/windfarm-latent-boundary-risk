# SETA全文补查：新增合法路径与实际结果

2026-10-20。目标文献：Yang Wang、Haiyun Wang，*Reserve-risk-oriented regime-calibrated interval forecasting for wind power integration under extreme fluctuations*，SETA94:105438，DOI [10.1016/j.seta.2026.105438](https://doi.org/10.1016/j.seta.2026.105438)。

**结论：仍未取得真实全文，没有新增足以改变上轮方法审查或投入决定的正文证据。** 本轮完成的是新增获取路径补查，不能称两篇近邻已全文核透。上轮16入口与判断保留在[旧审查](../../core_question_identification_20261020/seta/FULLTEXT_REVIEW.md)，未修改。

## 本轮新增路径

| 路径 | 实际结果 | 正确边界 |
|---|---|---|
| [作者机构主页：新疆大学王海云](https://dqxy.xju.edu.cn/info/1047/1658.htm) | 公开页面可读，论文/专著栏选列10篇论文，列至2024；页面未提供目标2026稿件或研究仓库链接 | 官方主页真实，不等于目标论文全文，也不证明作者在任何地方都未自存稿 |
| [CORE公开DOI搜索](https://core.ac.uk/search?q=10.1016%2Fj.seta.2026.105438) | web工具不可访问；普通浏览器出现Cloudflare安全验证页面，未进行挑战操作 | 未得到搜索结果，不能记为CORE零命中；另做站点定向公开索引检索，未返回目标全文 |
| [Unpaywall DOI API](https://api.unpaywall.org/v2/10.1016/j.seta.2026.105438) | 不带email的公开请求返回HTTP422，响应明确要求email参数；已保存原错误结果 | 未填写作者邮箱、未猜测用户邮箱、未伪造联系身份；不是查询成功或没有OA版本 |
| [Unpaywall官方API说明](https://data.unpaywall.org/products/api) | 文档要求email；说明search端点已于2026-09-18退出，并建议改用OpenAlex（同团队/同数据） | 上轮OpenAlex结果已保存：没有repository/PDF链接；不把两个相关索引当独立证明 |
| Elsevier同一标准文章API的application/pdf表示 | 一次无认证请求返回HTTP429；未重试，保存pdf_route_result.json | 没有取得PDF。纠正措辞：上轮Crossref实际只登记XML/plain两个TDM链接，没有登记application/pdf链接；本次是标准API表示探查，不是发现新的已登记PDF |
| DOI/title + CORE/Unpaywall/机构/作者/公开代码仓库定向检索 | 未发现该文新增可验证的公开全文URL；其他论文和无关结果不使用 | 这是本次有界检索结果，不是全文全球不存在的证明 |

具体请求/检索记录见[SOURCE_MATRIX.csv](SOURCE_MATRIX.csv)。没有重复访问上轮已限流的plain路径，没有猜signed URL，没有登录、付费、绕过验证、联系作者或下载测量数据。

## 为什么不能补写逐章结论

现有阅读等级仍为 `PUBLISHER_PREVIEW_PLUS_VERIFIED_METADATA`。完整工况时间公式、全部输入与currentP/history对照、精确horizon、校准分位/收缩规则、完整消融与统计均未取得。外场不重训/重校准以及备用终点为边界违约proxy，沿用上轮明确定位到公开贡献/引言的陈述，不能升级为全文复验。

本轮没有依据把预览变为全文，也没有依据补写任何“该文未来泄漏”“该文未做强对照”或“该文已经解决全部拟议问题”的结论。没有实际PDF，因此没有伪造页码、下载哈希或逐章阅读记录。

**执行结果：补查到此收束，不恢复实验或修改稿件；旧版本、旧决定和未闭合项原样保留。** 如之后由正常授权渠道取得论文原文，才有条件真正开展逐章核验；本轮不联系作者、不启动持续监控，也不将未来可能获得的正文计为已完成。
