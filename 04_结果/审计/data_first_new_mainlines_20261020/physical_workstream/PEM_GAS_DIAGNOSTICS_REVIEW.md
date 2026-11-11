# 物理工作流：PEM电解气体安全诊断的数据优先审查

日期：2026-10-20（Asia/Shanghai）。只读论文、官方数据说明和元数据；未下载测量CSV/ZIP，未运行实验。没有修改论文、PROJECT、科学契约或旧审计。

## 裁决

**NO_GO_AS_CURRENT_TOP_JOURNAL_MAINLINE。** 找到了有明确干预、协议标识和独立气体测量的数据，数据条件明显优于普通运行日志。但最直接的科学命题已经是伴随论文的贡献；剩余的跨材料/老化诊断迁移检验仅有四个单电池个案，未形成足够明确的新机制或独立验证范围。不将其包装成新的健康预测器、安全调度或conformal框架。

## 1. 数据资格先于题目

锁定数据：Steffen Brundiers，Datasets: Time-Resolved Performance and Stability of Different Gas Recombination Catalysts in PEM Water Electrolysis，2026，Zenodo具体版本19361280，CC BY 4.0。

直接字段与协议来源：[原作者所在大学的数据说明](https://research.uni-hannover.de/de/datasets/datasets-time-resolved-performance-and-stability-of-different-gas/)。这不是只查数据门户存在性。

|要素|官方元数据支持|边界|
|---|---|---|
|受控对照|Reference无复合催化层、PtNano、PtBlack、Pt/C四次实验；同类单电池结构、固定高压工况|每个文件对应一个样品，不是每种材料多批次重复|
|实验范围|4 cm²，Nafion N115，30bar阴极压力，80°C供水，约1500h|不能由此确认跨压力、跨温度、工业堆尺度泛化|
|激励与标识|conditioning、POL_GEIS、H2_char、CV_cycles、OCV、CstC_12A/GEIS_12A、CstC_1A/GEIS_1A；measurement_type_counter区分重复阶段|重复阶段不是独立新电池；需按协议与时间使用|
|电气及辅助量|elapsed_time_s、I_mA、E_V、Temp_degC、pressure_bar_abs、conductivity_uScm|温度是cell-block而非真实反应温度；PtBlack/PtNano约300–500h部分压力/电导缺测|
|独立读出|GC H2_uncorrected_vol_percent与稀释校正H2_corrected_vol_percent；EIS频率、幅值、相位|GC是不同测量通道，但校正浓度不是纯膜渗透通量的独立真值|
|采样|电气约1s；GC通常约90s；EIS仅专门步骤|不能秒级前填GC后当作大量独立安全标签；协议外NaN不自动插补|
|可复用许可|数据CC BY 4.0，附说明PDF和示例notebook|本轮未读取任何测量记录，未验证实际文件完整性|

## 2. 最接近原文核验

### 直接伴随论文：已读作者公开全文

Brundiers等，*Time-resolved performance and stability of different gas recombination catalysts in PEM water electrolysis*，EES Catalysis 4(5),1190–1209，2026，DOI10.1039/D6EY00106H。

- [作者机构元数据](https://research.uni-hannover.de/de/publications/time-resolved-performance-and-stability-of-different-gas-recombin/)
- [作者上传公开全文（ResearchGate）](https://www.researchgate.net/publication/407301556_Time-Resolved_Performance_and_Stability_of_Different_Gas_Recombination_Catalysts_in_PEM_Water_Electrolysis)
- 出版社正文在本工具未成功打开；使用上列作者全文核验，不把摘要当全文。

角色：mainstream/direct。原文已比较相同Pt负载的不同GRC配置、前后及中间气体浓度演化、初期约250h run-in、后期变化，以及OCV衰减与气体指标的相关性。其§2与§3.3明确测得的是经复合及其他过程影响的apparent crossover；§3.4讨论OCV多机制影响。电化学性能近似稳定并不意味着气体安全指标稳定，已属于原文问题与结果。

### 邻域反证（不冒充均已完成全篇精读）

|文献|角色/阅读层次|对候选的约束|
|---|---|---|
|Data-driven degradation analysis of proton exchange membrane electrolyzer stacks under dynamic load operation，Energy and AI2026，10.1016/j.egyai.2026.100790|mainstream；出版社方法/结果/附录HTML已读|Jülich两50kW堆1134h跨6年数据已有动态退化建模；随机点拆分和间接退化标签不提供新因果真值，不能以大数据量为受控寿命实验|
|Experimental demonstration of dynamic demand response scheduling for PEM-electrolyzers，Applied Energy2025|adjacent；作者PDF入口已定位、正文抓取未完成|动态负荷/温控/调度不是显然空白，不推荐该宽题|
|Hard-constraint physics-residual networks for hydrogen crossover prediction and high-pressure extrapolation in PEM water electrolysis，Applied Energy2026，10.1016/j.apenergy.2026.128220|adjacent；出版社方法段已读|已有跨文献184测量、物理约束crossover预测；不能把物理网络或压力外推当现成新方向|
|Dynamic degradation mechanisms of PEM water electrolysis membrane electrode assembly under multiple operating conditions，Applied Energy2026，10.1016/j.apenergy.2026.128221|adjacent；出版社方法概述/摘要已读|已有多动态负荷、电化学/结构损伤与可逆/不可逆退化研究；宽泛“动态效应比电压损失复杂”不能首创|

对应原文入口：[Energy and AI](https://doi.org/10.1016/j.egyai.2026.100790)、[Applied Energy动态调度作者稿](https://juser.fz-juelich.de/record/1042602/files/1-s2.0-S0306261925007445-main.pdf)、[气体预测](https://doi.org/10.1016/j.apenergy.2026.128220)、[多工况退化](https://doi.org/10.1016/j.apenergy.2026.128221)。这些引用用于反证宽泛新颖性，不以未读全文的工作证明穷尽性。

## 3. 最具体的剩余问题及识别上限

可证伪小问题是：**在固定30bar/80°C协议中，早期OCV衰减诊断与气体浓度的校准关系，能否迁移到后期或另一GRC配置；加入EIS或一次新的GC校准是否改变这一关系？**

这可以用现有协议重复阶段与GC读出做有限预测/诊断检验，但仍有三个不能跨过的边界：

1. GC出口浓度同时受膜渗透、膜内复合、阳极反应及流路影响。仅这些读出不足以分离唯一机理。不能把拟合残差命名为膜失效或Pt迁移的直接证据。
2. 每个GRC一个样品。把时间窗口随机拆分不会产生独立材料重复；留一GRC测试也只是一个样品域，不等于材料总体泛化。
3. 电压、HFR和OCV与gas的关系及其多机制解释已经在原文提出。增加一个回归器、交叉验证或校准策略，最多补一项有限诊断验证，不自动形成顶刊分量。

同理，安全阈值的穿越必须确有测量支持，不能将原论文假定的shutdown limit和长寿命外推改写为已观察失效事件。现有样品既不支持所有压力/温度下的安全包络，也不支持新动态控制策略的长期安全和寿命反事实。

## 4. 四问与去留

|四问|审查答案|
|---|---|
|Why care|高压电解气体交叉渗透约束低负荷运行，诊断错误有真实设计后果|
|What's new|宽题已被原文和近邻覆盖；剩余OCV迁移小题尚未形成超出原文潜在诊断结论的强增量|
|Why believe|协议、激励、GC和EIS较扎实；但单样品、单压力/温度与混合机制阻碍更强因果/泛化主张|
|Why venue|适合电化学与能源转换读者，但目前只是原研究的有限再分析，不足以推荐为新的顶刊主线|

**最终决定：否决本候选作为当前顶刊主线，不进入测量下载或实验。** 不能因数据确实比旧运行日志更好，就降低新颖性和独立验证门槛。本次没有证明PEM电解研究领域不存在新问题，只完成这组可公开、可核验数据所能支撑的候选审查。
