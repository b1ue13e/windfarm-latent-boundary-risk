# 原 grokking 可信访问与执行来源追查

日期：2026-10-18。**E07 保持未激活。** 用户随后确认原 grokking 是已销毁的租用算力云实例。收到该说明后，本智能体没有再对该地址发起网络访问，也不再请求新主机指纹。没有重新推理、改动原结果或修改信任配置。

## 结论

**未能通过可信路径访问原实例，2026-08-30 辅助预测的完整执行来源仍为 UNKNOWN / NOT CLOSED。** 这次找到了历史正确端口，但该端点返回的主机密钥与既有记录不符，严格校验阻止了认证及远端命令执行。用户确认原实例已销毁后，不能把该地址当前的服务视为原 grokking。

当前服务是谁、密钥为何变化、是否还有云平台磁盘快照或其他离线备份均 UNKNOWN。实例销毁与端点回收/重分配的解释相容，但本次没有验证回收过程，不将其写成事实。也没有声称登录后发现原目录或日志不存在——**本次根本没有进入远端文件系统**。

## 已有连接路径与严格拒绝记录

1. 当前 `C:\Users\lidong\.ssh\config` 仅配置 Metis；历史 `config.bak` 明确将别名 **grokking** 指向 `root@192.168.17.251:25329`，使用已有 identity 文件。应用现存的 managed connection 元数据也指向同一端口。它们是路由证据，不能代替 SSH 主机身份验证。
2. `known_hosts` 和 `known_hosts.old` 在 `[192.168.17.251]:25329` 下均保留同一 ED25519 指纹：
   `SHA256:oNc+CkuCXl8LGjk3kqlIPZhdp/i/VTb0gtd5oF0ctY8`。
   前次审计使用的默认 22 端口与这条记录不是同一个端点；前次失败记录原样保留。
3. 本次只对这条已有路由发起一次只读探测，强制使用 **`StrictHostKeyChecking=yes`、已有 known_hosts、`UpdateHostKeys=no`、既有 ED25519 算法**，禁止本地命令及转发，并采用 BatchMode。未使用主机别名重映射、新密钥学习、keyscan 信任或关闭校验的选项。
4. 当前服务返回的 **未受信指纹**是：
   `SHA256:qTTam8cM3VllUiId9B76j+bK/FhOqskpd10eXfRVcLU`。
   OpenSSH 报 `Host key has changed`，exit **255**；认证未成功，stdout 为空，所请求的 hostname/原目录探测命令未执行。原始输出保留于 [connection_stderr.txt](connection_stderr.txt)、[connection_stdout.txt](connection_stdout.txt)。
5. 四份 SSH 配置/信任文件前后 SHA256 相同；没有删除旧条目、接受新指纹或读取/复制私钥材料到证据包。配置的 OpenSSH identity 路径仅用于标准客户端身份发现；拒绝发生在主机认证阶段，未进入远端用户认证成功阶段。

完整参数、旧指纹来源及前后哈希见 [trusted_path_preflight.json](trusted_path_preflight.json)、[connection_verification.json](connection_verification.json)、[trust_decision.json](trust_decision.json)。应用/编辑器等既存配置的只读检查未提供可独立认证的新路径；没有改用别的端口来绕过这次密钥不匹配。

## 用户确认原实例销毁

用户的原话为：“这个ssh已经连接不上了，销毁了，是我租的算力云”。本次将其作为 **USER-CONFIRMED** 的实例状态记录，而不是远端检查结果，见 [instance_disclosure.json](instance_disclosure.json)。

该说明取代了此前关于提供可信新指纹的异步信息请求：不再需要用户为已经销毁的实例接受任何新密钥。原实例准确销毁日期、原数据卷是否仍在、服务商是否有快照，均未获得证据。

## 本地留存核查及范围

在远端访问被拒绝、随后确认实例销毁后，只继续本地读取：

| 检索范围 | 本次观察 | 不能据此推出 |
| :--- | :--- | :--- |
| 1415 份既有项目日志/输出文件 | 未命中 `trainweight_full_rerun_20260830` 或 `paper3_audit_rerun_20260830` 两条目录标识 | 不能断言其他命名的日志不存在 |
| 320 个已盘点本地归档的成员名 | 未找到带两条目录标识的目标 JSON/log/权重成员；未向原目录解包 | 不是对所有嵌套成员内容的全文检索 |
| 本地历史消息库与运行日志 SQLite | 只读查询上述标识、记录日期早于 2026-09-05，零命中；不复制无关消息或凭据 | 不能证明当时没有运行或其他存储中没有日志 |
| 2026-09-04 旧项目索引备份 | 114 个匹配中文项目 cwd 的 rollout 索引，当前所指文件均缺失；元数据没有落在 8 月 29 日—9 月 2 日范围的记录 | 索引不是原评估日志，也不代表原远端或其他备份已被穷尽 |
| 当前/旧索引中的 ASCII 项目别名 | cwd 包含 paper3 或 windfarm-latent-boundary-risk 的追加查询零命中 | 不补造缺失的执行事件 |

查询采用 SQLite 只读模式；没有复制或修改数据库。范围及定位信息见 [local_original_log_search.json](local_original_log_search.json)、[local_original_archive_search.json](local_original_archive_search.json)、[local_august_log_index_search.json](local_august_log_index_search.json)、[additional_project_index_search.json](additional_project_index_search.json) 和 [local_recovery_summary.json](local_recovery_summary.json)。

上述结果是**限定范围内未复得原评估日志**，不是全局不存在证明。用户若日后提供销毁前导出、磁盘快照或其他留存，仍可作为新来源审计；本次没有联系服务商、创建新实例或重跑实验来补写历史事实。

## 执行来源的当前边界

| Claim / 待闭合环节 | 直接证据 | 当前状态 |
| :--- | :--- | :--- |
| 旧 grokking 路由为 25329，而非前次默认 22 | 旧配置、既存 managed connection 和已有 known_hosts 记录 | VERIFIED，路由/旧信任记录范围 |
| 本次端点密钥与既有 pin 不一致，访问在认证前被拒绝 | OpenSSH 原始 stderr、exit255、空 stdout | VERIFIED；新服务未认证为原实例 |
| 原租用实例已销毁 | 用户直接说明 | USER-CONFIRMED；不代表备份可用性已验证 |
| 2026-08-30 原评估的实际权重、完整输入及数值环境已绑定 | 本次没有可信远端执行记录；限定本地检索未复得 | UNKNOWN / NOT CLOSED |
| 先前当前权重与 10 月 15 日静态哈希一致可以替代原执行凭证 | 仅为后期文件身份记录 | 不支持升级；既有结果与 UNKNOWN 保留 |
| 辅助预测与旧 yhat 的差异可改判精确或唯一归因于浮点 | 本次没有新的数值执行证据 | 不支持；10/10 非精确与原因 UNKNOWN 不变 |

可用于文稿的有界表述：

> The original rented compute instance has been reported destroyed. A strict SSH check rejected a changed host key before authentication, and no remote commands were executed. The scoped local search did not recover the original evaluation receipts; generation-time weight, input and numerical-environment bindings therefore remain unverified.

## 保护及验证

没有修改原评估日志、预测、权重、输入、SSH 配置或既有审计记录。没有恢复主机信任、重新推理或构造替代结果。E07 协议及其空绑定继续保留。证据包只包含新的只读观察、指纹/哈希、原始拒绝输出及报告；不包含私钥或认证秘密。

最终校验：四份 SSH 配置/信任文件与访问前哈希一致，255 个既有受保护文件与前次快照一致。E07 三项激活绑定及确认性数据清单仍为空，合格窗口数为 0。既有 E07/旧 yhat 审计测试 **13 passed**，两项科学/数字门禁通过；不构成原评估来源认证。完整绑定见 [audit_manifest.json](audit_manifest.json)，校验见 [verification.json](verification.json)。
