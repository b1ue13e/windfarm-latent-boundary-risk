# Metis 实际历史准备与双 worker 预检

**VERIFIED：实际 prepare 和首两个历史 worker 的字节、来源与执行范围核对通过，未发现阻断继续运行冻结历史数组的问题。** 本报告不释放作业、不认证完整历史包，也不授予2025解封资格。

审查时间：2026-10-19 04:13:49 UTC；直接通过既有 metis SSH 连接只读核对。远端根目录：`/lstr/sahara/minlpml/junyu/independent_confirmation_20261019_v1`。未执行 qrls、qalter、训练、预测、校准或 bootstrap；未打开、列成员或解析2025年包。以下是该时点实际文件证据，不能把后续调度状态推定为完成。

## 执行来源

- deployment commit：`24153f857bb0f1e62b041cd5924c2d3bae562f44`。
- 协议SHA256：`27ba6498427ca425978f6674f013862ba272049f778562cb839969cb7f3bbc33`。
- 远端53项声明源码逐项实际哈希与deployment/preflight一致；deployment文件清单逐项实际SHA256没有不符项。
- 独立review状态为 `PASS_FOR_PRE_UNLOCK_IMPLEMENTATION`，无阻断；56项review来源逐项实际匹配，deployment中的review绑定匹配。
- review SHA256：`719ec44f601ef81c494a79cabb84649bfa6806b5fa80e6e202446df6fa78abd5`。
- 实际preflight为PBS `244727.cm`，exit_code=0，日志为 **25 passed in 4.60s**；记录的协议、源码和commit均与当前deployment一致，测试期间source_unchanged=true。

## 实际 prepare

PBS `244727.cm`，cn13，CPU；2026-10-19 04:11:42.566012至04:12:01.473386 UTC，状态 `COMPLETE`。

- prepared manifest的8个成员均逐项大小/SHA256匹配，受保护输入的实际哈希均匹配receipt；receipt源码/协议与当前一致。
- prepared manifest SHA256：`360801f9355000ca77ef2085f798f344afc0d97df7fdd4040533281b2005dacc`。
- `point_last_label_release=26057 < first_forecast_publication=26058`，实际训练满足已修正的发布前标签成熟断言。
- 已封存原始边界：turbine字段形状21×4、grid字段形状21×2；两个seen数组均为21/21。它们保留六个原消费字段，而非均值后的四通道比较。
- 记录环境：Python3.11.16、NumPy2.4.6、pandas2.3.3、sklearn1.9.1、Torch2.11.0+cu128；backend明确为CPU，不因Torch CUDA构建版本推定使用GPU。

## 实际双 worker

两者均为PBS `244728.cm`、cn13、pitch_withheld/Common、**实际seed仅201**。receipt配置虽声明完整201—205五实例，不能把这两个worker说成五seed完成。

| worker | 估计器 | 实际UTC起止 | fit秒 | 归档核对 |
|---|---|---|---:|---|
| 0 | HGB | 04:12:06.929639—04:12:12.480461 | 1.291193668 | COMPLETE，6成员大小/SHA通过 |
| 1 | MLP | 04:12:15.612342—04:12:45.618529 | 27.812059280 | COMPLETE，6成员大小/SHA通过 |

两个worker的源码、协议、受保护输入实际哈希均匹配；selection的anchors、forecast、true、mask、shortfall五项identity完全相同。两者均使用360,000个唯一训练索引，索引SHA完全相同：`4231beefa2ec26944c70af4b927500a7387150067075049566ec8f4a7b1309e6`。

MLP保存完整80轮有限训练轨迹，首/末训练损失约0.180359/0.157119。这只验证训练执行及记录，不认证优化充分或泛化性能；本预检不对历史成本/风险结果作效果选择。

输入scope与冻结实现一致：Common的原始新增输入宽度为4（共同预测、sin/cos时钟、机组ID），资源元组 `[0,1,4]`。共同预测器本身仍来自历史W/P，因此不是端到端“无风速/功率”的模型。MLP标准化与目标尺度只来自本次历史拟合样本；延迟/缺pitch只改变备用层输入，不是现场端到端延迟认证。

## 尚未闭合的门禁

核对时 `results/UNLOCK_EVENT.json` 不存在、chosen目录不存在。2025仍未解封，完整550历史worker、全部五seed、完整历史choices及freeze尚未核验。本次不把首两个worker的通过升级为这些阶段已完成。

可以据此继续冻结历史数组；原任务0/1由existing分支验证已有归档后复用，不应覆盖重训。解封作业继续held，须在全部历史完成后实际复验模型/offset/样本/forecast/raw-boundary、source/config/commit/preflight/review及choices/freeze绑定。

数组stdout隔离属于主执行者随后报告的调度变更，本报告未修改或单独验证其调度属性；它不能改变数值源码或本报告的统计/来源边界。
