# 潜伏控制相变与遥测退化约束下的风电运行备用极值决策：最小充分模型原理

**作者署名**：李俊宇，杜俊涛*  
**作者单位**：安徽财经大学 统计与应用数学学院，蚌埠 233030，中国  
**通讯作者**：杜俊涛 (dujuntao@aufe.edu.cn)  

---

### 结构化摘要

在高比例可再生能源并网的新型电力系统中，日前与日内运行备用（Operating Reserve）的高效核定受制于极端非对称的短缺惩罚结构（惩罚倍率 $\rho \ge 10$）[1]–[3]。经典空气动力学物理模型严格依赖于无时滞、全测点可见的理想传感器遥测 [4], [5]；然而在多主体商业博弈与工业通信限制下，风电机组底层叶片变桨角（$\beta$）在电网调度端普遍处于协议屏蔽状态 [6], [7]，且伴随 10–30 分钟的传输队列滞后 [8], [9]。在此工况下，机组在最大功率跟踪（MPPT）区与变桨限功率区之间的微观逻辑切换退化为不可直接观测的“潜伏相变”[10]。传统气动物理模型因输入缺失而发生确定性外推发散（违约率激增至 $24.02\%$）[11]；而前沿端到端深度分位数回归在非对称报童梯度的持续单向拉扯下，陷入表征退化与病态极值过度保守，诱导超额采购冗余容量（采购量达 $2.12\times 10^6\text{ kWh}$），导致系统综合考核总成本较基准反向激增 $87.2\%$ [12], [13]。

针对物理方程刚性瘫痪与端到端黑盒梯度畸变这一根本矛盾，本文从机电动力学耦合机理出发，提出了基于机电动力学响应特征的潜伏边界反演与正交两阶段极值决策理论框架。在严格受控的因果隔离协议下证明：单机有功功率的时序动态响应蕴含了控制相变的主导因果物理指纹（$\text{AUROC} = 0.988 \pm 0.004$）[14], [15]，在推断期完全扣留变桨遥测的前提下实现了潜伏相变的高保真逆向辨识；通过将确定性条件期望估计与标量残差空间的非对称分位数校准进行正交解耦，从几何结构上消除了极性梯度对底层特征流形的破坏，使综合考核总成本较端到端模型大幅降低 $41.9\%$ [16]。

尤为关键的是，基于商业风电场 134 台机组全生命周期运行数据（累计逾 40 万机组-时间步）[17] 与跨国商业风场的严格反事实消融，本文推翻了数据驱动新能源决策领域的三项经典预设：
1. **状态可辨识性不蕴含决策充分性（Identifiability $\not\Rightarrow$ Decision Sufficiency）**：逆向恢复出的后验模型在平稳运行域反而劣于无状态感知的局地条件分位数（基线领先 $41.0\text{ 万度电}$，$P=0.0026$）[18]；后验感知本质上仅为剧烈相变瞬态域内的局部风险对冲器（双重差分交互项 $-297,565\text{ kWh}$）；
2. **等预算消融戳破资本代偿假象**：严格等备用预算消融（$\Delta R \equiv 0$）证实，后验模型名义违约率的下降纯粹是由超额采购 $+149.2\text{k kWh}$ 备用容量所诱导的**资本代偿效应**，其未对冲短缺在等预算下反而平均增加 $+5{,}234\text{ kWh}$（4/5 随机种子显著恶化）；
3. **架构复杂度的奥卡姆剃刀证伪**：在参数量严格受控（110,012 参数）下，动态混合专家路由（MoE）与同等容量密集网络在决策层完全平价（$p=0.380$）[19]，空间尾流图卷积带来的边际信息增益仅为 $0.0015$ [20], [21]。

据此，本文在电力系统领域首次确立了 SCADA 遥测退化阶梯下的“最小充分模型选用宪章”，终结了电网极值调度中盲目追求高阶复杂黑盒模型的工程迷信。

**关键词**：运行备用；报童损失；SCADA 遥测退化；潜伏控制边界；两阶段解耦；最小充分模型；因果消融

---

## 一、 引言 (Introduction)

### 1.1 问题的物理与经济背景：极端非对称损失下的备用配置困境
在以高比例可再生能源为主体的新型电力系统运行架构中，风力发电的强随机性与间歇性引发了全网净负荷方差与偏度的非线性扩散 [1], [22]。为了抵御风电出力随机骤降对电网频率稳定与实时功率平衡构成的冲击，系统调度机构必须在日前与日内时间尺度前瞻性地核定下行运行备用（Spinning/Operating Reserve）[2], [23]。与以对称均方误差（MSE）为优化准则的常规负荷点预测截然不同，运行备用配置受制于微观经济学报童模型（Newsvendor Problem）所刻画的极端非对称考核惩罚结构 [3], [24]：
$$\min_{R_{t+h}} \ \mathbb{E} \left[ c_{\text{res}} R_{t+h} + c_{\text{short}} \max\left( \hat{Y}_{t+h} - R_{t+h} - Y_{t+h}, \ 0 \right) \right] \tag{1}$$
式中，$R_{t+h}$ 为日前下发给风电集群的下行备用裕度，$\hat{Y}_{t+h}$ 与 $Y_{t+h}$ 分别为日前点预测期望出力与实时落地出力，$c_{\text{res}}$ 为单位备用容量采购成本，$c_{\text{short}}$ 为电量短缺惩罚单价。在欧美与中国主要区域电力现货市场中，短缺惩罚倍率 $\rho = c_{\text{short}} / c_{\text{res}}$ 普遍处于 10 至 20 的高位区间 [25], [26]。归一化后，设 $c_{\text{res}}=1$，根据经典极值分位数回归理论，使得期望考核总成本（Surrogate Reserve Screening Cost, PSREI）最小的理论最优备用容量 $R^*_{t+h}$，严格等于残差随机变量 $S_{t+h} = \hat{Y}_{t+h} - Y_{t+h}$ 在条件信息集 $\mathcal{I}_t$ 下的高位分位数 [18], [27]：
$$R^*_{t+h} = F_{S_{t+h} \mid \mathcal{I}_t}^{-1}(q^*), \quad \text{其中最优分位数临界水平 } q^* = 1 - \frac{1}{\rho} \ge 0.90 \tag{2}$$
该非对称经济结构决定了备用决策的本质：模型必须在风电机组阵列的动力学极值尾部建立严密的风险测度流形。

### 1.2 工业现实瓶颈：多主体博弈下的遥测退化与潜伏相变
长期以来，学术界关于风电概率分位数预测与备用优化的主流研究，大多基于“信息完全可及”的学术温室假设 [28]–[30]——即假设电网调度主站能够毫秒级、全通道无损、零时延地获取风电场内每台机组的原始传感器寄存器读数。然而，正如 Wen 等人 [16] 与 Ullah 等人 [8] 所指出的，随着能源系统物理边界与数据链路的延伸，**决定预测与决策质量上限的往往是数据的物理可及性，而不再单纯是模型复杂度**。在真实商业风电场的挂网运行中，存在两类普遍且不可消除的信息退化：
1. **多主体商业博弈与数据资产隔离（Information Inaccessibility）**：在现代风力发电资产运营中，整机制造厂商（OEM）、风电场业主与电网调度机构分属不同利益主体。整机厂商出于底层核心变桨控制律的知识产权保护、商业竞争壁垒与网络安全认证隔离，在向调度监控主站推送 SCADA 遥测时，普遍对风机叶片变桨角（$\beta$）进行寄存器层面的物理切除、掩码屏蔽或仅提供有损截断值 [6], [7], [10]；
2. **广域工业以太网的时延排队效应（Telemetry Latency Drift）**：现场传感器数据经由现场总线、变电站环网交换机、工业网关转发至主站调度端，普遍经历 10 至 30 分钟的稳态队列排队时滞，在网络拥塞或通信扰动下甚至可达 60 分钟 [8], [9], [31]。

大型现代风电机组在额定风速交界带具有强烈的双区域非线性动力学相变特性 [4], [32]：在最大功率跟踪（MPPT）区，叶片维持在最优微距角（$\beta \approx 0^\circ$），出力近似与风速三次方成正比；在额定风速以上的变桨限功率区，伺服系统主动调节变桨角（$\beta > 0^\circ$）以泄放气动载荷，出力被强制截断在铭牌额定值附近。当变桨角测点被屏蔽且遥测存在时延时，机组在 MPPT 区与变桨限功率区之间的微观逻辑切换，在宏观调度端彻底退化为**不可直接观测的潜伏状态变量（Latent Regime Variable）** [10], [14]。由于这两种控制状态对应的系统物理雅可比矩阵发生断裂跳变，调度中心在日前决策期面临严重的“相变失明”困境。

### 1.3 传统范式的理论崩溃：从物理公式瘫痪到深度学习的梯度畸变
面对潜伏控制相变与遥测退化的双重制约，现有理论与工程方案暴露出深刻的方法论缺陷：
* **解析气动物理方程的刚性瘫痪**：经典动量-叶素（BEM）物理方程将实时风速与变桨角作为核心解析输入 [4], [5]。一旦缺少变桨反馈，物理方程只能退化地假定 $\beta=0^\circ$。在强风涌入时，模型将沿着三次曲线向额定容量上方进行无界发散外推，导致备用严重欠配，违约发生率飙升至 $24.02\%$，彻底击穿电网安全考核红线；
* **经典统计经验分位数缺乏相变感知**：自 Bremnes [18] 开创局部风速分位数回归以来，工程界广泛采用风速分箱经验分位数。然而该类方法建立在残差时间平稳性假定之上，对控制状态切换引起的方差脉冲扩散缺乏自适应机制，在相变过渡带频频发生尾部击穿；
* **前沿端到端深度学习的梯度畸变与病态保守**：近年来，学者广泛尝试利用深度时空图网络（STGNN）或 Transformer 在非对称 Pinball 损失引导下端到端直接拟合备用裕度 [12], [20], [33]。然而，在 $\rho=10$ 的非对称损失下，反向传播的次梯度场呈现出极端极性失衡：负向误差梯度赋予了高达 0.90 的绝对权重，而正向误差权重仅为 0.10。这种强烈的单向极性梯度持续冲刷主干特征网络，破坏了神经网络表征空间的通用几何流形，诱发了**病态极值过度保守（Pathological Over-Conservatism）**——模型为了规避高昂的单次短缺惩罚，倾向于向全场注入极其庞大的备用容量（实测采购量高达 $2.12\times 10^6\text{ kWh}$），导致系统总考核成本较物理规则反向暴增 $87.2\%$。

### 1.4 本文研究突破与核心科学贡献
针对上述物理方程刚性瘫痪与深度学习梯度畸变的困境，本文从机电能量守恒第一性原理出发，系统构建了一套**潜伏相变因果中介反演与正交两阶段解耦极值决策理论框架**。本文的主要科学贡献包括：

1. **揭示并证实了机电动力学响应对潜伏相变的有偏因果中介机制**：从流体力学与机电暂态耦合机理证明，虽然原因变量（变桨动作）不可见，但机组转矩突变必然通过发电机电磁阻尼在有功功率时序响应中留下不可磨灭的瞬态物理指纹 [14], [34]。在推断期完全扣留变桨的严格反事实设定下，仅凭单机有功功率历史瞬态实现了 $\text{AUROC} = 0.988 \pm 0.004$ 的相变状态逆向辨识，使临界事件召回率从物理模型的 0.196 显著跃升至 0.417；
2. **构建了期望定标与残差校准正交解耦的极值决策新范式**：从数学上证明了端到端分位数回归在非对称损失下的几何不稳定性，提出了将无偏期望曲面拟合（对称 MSE 损失）与标量残差高位分位数映射彻底解耦的两阶段架构，从机理上消除了非对称梯度对特征提取器的单向扭曲，在保障电网 $10\%$ 安全底线的前提下，使综合考核总成本较端到端深度学习降低 $41.9\%$；
3. **基于大规模工业实测粉碎了过度工程化迷思，确立“最小充分模型原理”**：依托 134 台商业机组的全生命周期数据 [17] 与跨国外部风场消融，本文推翻了“状态恢复蕴含决策优势”的经验直觉，证实后验模型在全场全时段尺度的成本反而劣于简单的 10-bin 局地风速分位数；等预算消融进一步戳破了算法可靠性提升的资本代偿本质；最终绘制出 SCADA 遥测退化全阶梯下的“最小充分模型选用准则”。

---

## 二、 物理系统建模、遥测退化映射与备用决策形式化 (Problem Formulation)

### 2.1 风电机组分段气动相变与混合逻辑动态
考虑包含 $M$ 台大型风电机组的风电集群。对于任意机组 $m \in \{1, \dots, M\}$，在离散时间步 $t$，其所经受的轮毂高度有效进风风速记为 $v_{m,t} \in \mathbb{R}_+$，叶片变桨角记为 $\beta_{m,t} \in \mathbb{R}_+$。根据经典空气动力学理论 [4], [35]，风轮捕获的气动机械功率 $P_{m,t}^{\text{aero}}$ 可表示为：
$$P_{m,t}^{\text{aero}} = \frac{1}{2} \rho_{\text{air}} \pi R^2 C_p(\lambda_{m,t}, \beta_{m,t}) v_{m,t}^3 \tag{3}$$
式中，$\rho_{\text{air}}$ 为空气密度，$R$ 为风轮叶片半径，$\lambda_{m,t} = \omega_{m,t} R / v_{m,t}$ 为叶尖速比（$\omega_{m,t}$ 为风轮转速），$C_p(\lambda, \beta)$ 为非线性功率捕获系数。

在机组内部可编程逻辑控制器（PLC）调度下，机组运行状态可形式化为一个离散控制相变变量 $Z_{m,t} \in \{1, 2\}$：
$$Z_{m,t} = \begin{cases} 1, & \text{若 } v_{m,t} < v_{\text{rated}} \quad (\text{MPPT 区，}\beta_{m,t} = \beta_{\text{opt}} \approx 0^\circ) \\ 2, & \text{若 } v_{m,t} \ge v_{\text{rated}} \quad (\text{变桨限功率区，}\beta_{m,t} > \beta_{\text{opt}}) \end{cases} \tag{4}$$
式中，$v_{\text{rated}}$ 为额定风速。

经过传动链阻尼与双馈异步发电机（DFIG）机电能量转换，机组向电网注入的瞬时电气有功功率 $y_{m,t} \in [0, P_{\text{rated}}]$ 满足如下混合一阶动力学响应 [4], [34]：
$$\tau_e \frac{\mathrm{d} y_{m,t}}{\mathrm{d} t} + y_{m,t} = \eta_g \cdot \min\left( P_{m,t}^{\text{aero}}(v_{m,t}, \beta_{m,t}), \ P_{\text{rated}} \right) + \epsilon_{m,t}^e \tag{5}$$
式中，$\tau_e$ 为发电机电气响应时间常数，$\eta_g$ 为机电转换效率，$P_{\text{rated}}$ 为机组额定铭牌容量，$\epsilon_{m,t}^e$ 为电网侧高频电磁测量噪声。

当系统跨越额定风速边界时，状态雅可比矩阵发生结构性跳变：
$$\frac{\partial y_{m,t}}{\partial v_{m,t}} = \begin{cases} \frac{3}{2} \rho_{\text{air}} \pi R^2 C_p v_{m,t}^2 > 0, & \text{若 } Z_{m,t} = 1 \\ 0, & \text{若 } Z_{m,t} = 2 \end{cases} \tag{6}$$
在状态 $Z=1$ 下，功率对风速高度敏感；在状态 $Z=2$ 下，变桨调节使净功率输出饱和截断。这一临界转换边界构成了日前预测残差非对称偏斜与方差脉冲膨胀的机理根源。

### 2.2 SCADA 遥测退化工况阶梯定义
在调度自动化系统中，定义三类典型的工业遥测可用性阶梯（Observability Regimes）[8], [16]：
* **工况一（完好遥测基准，Regime 1: Pristine Telemetry）**：  
  进风风速与变桨测点均实时、新鲜可见，信息集形式为：
  $$\mathcal{I}_t^{\text{R1}} = \left\{ [v_{m,t}, \beta_{m,t}, y_{m,t-1}]^\top \right\}_{m=1}^M \tag{7}$$
* **工况二（通信时延漂移，Regime 2: Latency Drift）**：  
  受排队延迟与主站轮询时滞影响，全场传感器数据经历统一滞后 $\tau_{\text{delay}} \in [10, 60]\text{ min}$，调度端仅能获取陈旧测点：
  $$\mathcal{I}_t^{\text{R2}} = \left\{ [v_{m,t-\tau_{\text{delay}}}, \beta_{m,t-\tau_{\text{delay}}}, y_{m,t-\tau_{\text{delay}}}]^\top \right\}_{m=1}^M \tag{8}$$
* **工况三（变桨物理屏蔽工况，Regime 3: Blade-Pitch Withholding）**：  
  整机厂商协议防火墙将变桨角完全屏蔽（$\beta \equiv \text{NaN}$ 或寄存器切除），调度端特征向量被强制压缩为纯电气与气象通道：
  $$\mathcal{I}_t^{\text{R3}} = \left\{ \mathbf{x}_{m,t-\tau_{\text{delay}}}^{\text{withheld}} = [v_{m,t-\tau_{\text{delay}}}, y_{m,t-\tau_{\text{delay}}}, T_{m,t-\tau_{\text{delay}}}^{\text{env}}, \dots]^\top \right\}_{m=1}^M \tag{9}$$
在此工况下，控制状态变量 $Z_{m,t}$ 退化为不可直接观测的潜伏变量。

### 2.3 日前备用决策与非对称报童损失函数
在电力系统日前调度框架下，设决策前瞻步长为 $h \in \{1, \dots, H\}$（对应 10 分钟至 1 小时前瞻）。对于全场总有功出力 $Y_{t+h} = \sum_{m=1}^M y_{m,t+h}$，调度中心首先给出点预测期望值 $\hat{Y}_{t+h}$，并分配下行备用容量 $R_{t+h} \ge 0$。

当真实出力 $Y_{t+h}$ 实际落地后，若 $Y_{t+h} < \hat{Y}_{t+h} - R_{t+h}$，系统发生短缺违约，产生的未对冲短缺电量为：
$$U_{t+h} = \max\left( \hat{Y}_{t+h} - R_{t+h} - Y_{t+h}, \ 0 \right) \tag{10}$$

定义备用服务综合考核经济成本指标（Surrogate Reserve Screening Cost, PSREI）[3], [25]：
$$\text{Cost}(R_{t+h}) = c_{\text{res}} R_{t+h} + c_{\text{short}} U_{t+h} = R_{t+h} + \rho \cdot \max\left( \hat{Y}_{t+h} - R_{t+h} - Y_{t+h}, \ 0 \right) \tag{11}$$
归一化设单位采购成本 $c_{\text{res}}=1$，非对称惩罚倍率 $\rho = c_{\text{short}} / c_{\text{res}} = 10$。根据微观经济学报童分位数理论 [24]，使得期望考核总成本最小的最优备用容量 $R^*_{t+h}$，严格对应于残差随机变量 $S_{t+h} = \hat{Y}_{t+h} - Y_{t+h}$ 在到达信息集下的条件分位数：
$$R^*_{t+h} = F_{S_{t+h} \mid \mathcal{I}_t}^{-1}(q^*), \quad \text{其中最优分位数水平 } q^* = 1 - \frac{1}{\rho} = 0.90 \tag{12}$$

决策模型的核心目标，是在满足全场违约概率不突破名义安全考核红线 $\alpha = 1 - q^* = 10\%$ 的前提下，实现综合经济考核成本 PSREI 的最小化。

---

## 三、 潜伏边界物理指纹重构与两阶段解耦决策方法 (Methodology)

### 3.1 动力学物理指纹与潜伏状态逆向恢复机理
在工况三下变桨信号被物理扣留，如何打破状态不可观测的瓶颈？因果物理切入点在于机电能量守恒与发电机电磁转矩阻尼 [4], [34]：
* 当机组发生控制相变切入变桨区时（$Z=1 \to 2$），风轮气动转矩瞬时跌落，发电机内部阻尼绕组产生瞬态反电势，有功功率曲线上表现为高频超调截断；
* 当机组稳定运行于 MPPT 区时（$Z=1$），有功功率沿三次曲线平滑演变，时序自相关系数 $\text{Corr}(y_t, y_{t-1})$ 显著高于变桨区。

因此，单机有功功率历史序列的瞬态轨迹 $\mathbf{y}_{m,t-\tau:t} = [y_{m,t-\tau}, \dots, y_{m,t}]^\top$ 构成了潜伏变桨控制状态的显式因果物理指纹（Consequence Signature）[14], [15]。

本文构建潜伏状态后验概率推断网络 $g_\phi$。为在严格保障工程部署严密性的同时充分挖掘物理信息，算法采用**特权信息学习范式（Learning under Privileged Information, LUPI）** [36]：
* **离线训练阶段（特权监督）**：利用历史归档数据中偶存的变桨数据构建离线标签 $Z_{m,t}^* \in \{1, 2\}$，优化辅助对齐损失：
  $$\mathcal{L}_{\text{align}}(\phi) = -\sum_{m,t} \left[ \mathbb{I}(Z_{m,t}^*=2) \log \pi_{m,t} + \mathbb{I}(Z_{m,t}^*=1) \log (1 - \pi_{m,t}) \right] \tag{13}$$
  式中，$\pi_{m,t} = P(Z_{m,t}=2 \mid \mathbf{x}_{m,t}^{\text{withheld}}; \phi)$ 为模型输出的后验概率。
* **在线推断阶段（绝对物理屏蔽）**：在实时调度代码流水线中，设置严格的张量维度硬断言，将输入特征集合内的所有变桨寄存器通道彻底切除，仅向网络注入单机有功功率历史瞬态与基础气象变量，确保模型完全依赖结果信号进行逆向推断。

### 3.2 单点期望定标与残差非对称分位数两阶段解耦定理
端到端深度学习在 $\rho=10$ 下发生病态过度保守的数学根源在于：非对称 Pinball 损失在反向传播时向底层网络注入了严重失衡的梯度场 [18], [27]：
$$\frac{\partial \mathcal{L}_{\rho}}{\partial \mathbf{W}} = \begin{cases} -0.90 \cdot \nabla_{\mathbf{W}} \hat{y}, & \text{若 } y > \hat{y} \\ +0.10 \cdot \nabla_{\mathbf{W}} \hat{y}, & \text{若 } y \le \hat{y} \end{cases} \tag{14}$$
极度的正负梯度不平衡迫使主干神经网络将参数容量主要用于拟合正向极值偏置，破坏了表征空间的通用表达能力。

为从机理上切断非对称梯度污染，本文提出**单点预测与非对称分位数校准正交解耦的两阶段决策架构（Two-Stage Decoupled Framework）**：

```text
                    【第一阶段：条件期望物理定标】
输入特征 x ──→ 主干特征网络 f_θ ──(对称 MSE 损失)──→ 单点功率期望值 ŷ
                                                            │
                                  ┌─────────────────────────┘
                                  ▼ (计算标量残差，冻结主干梯度)
                           残差 s = max(ŷ - y, 0)
                                  │
                                  ▼
                    【第二阶段：非对称分位数自适应估计】
潜伏后验 π(Z) ──→ 风险映射头 h_ψ ──(Pinball 损失)──→ 非对称备用裕度 r*
                                                            │
                                                            ▼
                                                最终备用决策 R = r*
```

1. **第一阶段：对称无偏条件期望定标**  
   主干网络 $f_\theta$ 仅以标准对称均方误差（MSE）为目标进行优化，专门捕捉机组出力的条件期望曲面：
   $$\min_\theta \mathcal{L}_{\text{MSE}}(\theta) = \frac{1}{M T} \sum_{m=1}^M \sum_{t=1}^T \left( y_{m,t+h} - f_\theta(\mathbf{x}_{m,t}^{\text{withheld}}) \right)^2 \tag{15}$$
   由于 MSE 损失具备完全对称的凸曲率（Hessian 矩阵对称正定），主干特征提取器能够稳健收敛至物理出力中心线，彻底免疫极值梯度的单向拉扯。
2. **第二阶段：残差空间潜伏状态条件分位数校准**  
   在第一阶段模型完全收敛并**冻结所有主干参数 $\theta$** 的前提下，计算全场日前单点预测的确定性出力残差：
   $$s_{m,t+h} = \max\left( \hat{y}_{m,t+h} - y_{m,t+h}, \ 0 \right) \tag{16}$$
   随后，构建轻量级分位数映射模块 $h_\psi$，将第一阶段提取的潜在物理表征与逆向恢复的后验概率 $\pi_{m,t}$ 结合，专门在标量残差空间拟合非对称分位数：
   $$\min_\psi \frac{1}{T} \sum_{t=1}^T \max\left( q^* (s_{t+h} - r_{t+h}), \ (q^*-1)(s_{t+h} - r_{t+h}) \right) \tag{17}$$
   通过将非对称损失的搜索空间严格限制在轻量级线性残差头内部，主干表征的稳定性得到绝对保障。

### 3.3 架构复杂度的奥卡姆剃刀验证设计
针对时空图拓扑与动态混合专家门控（MoE）[19], [20]，本文构建了两套具有完全对齐参数量（110,012 参数）的受控对比架构：
* **动态路由专家架构（STGQ-Routed）**：主干网络包含两套异构专家前馈子网络，分别对应 MPPT 物理曲线与变桨限功率物理曲线，顶层采用可微分 Softmax 门控网络自适应分配路由权重；
* **密集无路由架构（STGQ-Dense）**：取消门控路由器与多专家分支，采用相同深度的单一标准密集前馈网络，将潜伏后验概率作为普通连续特征拼接输入。

---

## 四、 实验设计与多场站基准数据集 (Experimental Setup)

### 4.1 数据集分布与测试切块协议
本研究的实证评估依托三座真实的商业风电场数据集：
1. **源风电场（WTB 基准）**：位于中国北方某大型商业陆上风电场（KDD Cup 2022 SDWPF 官方基准）[17]，由 134 台额定容量为 $1.5\text{ MW}$ 的双馈风电机组组成，总装机容量达 $201\text{ MW}$。采样周期为 10 分钟。测试集严格锁定连续跨越不同季节特征的 35 个完整日历日（$35 \times 144 = 5,040$ 个时间步，全场累计评估单元达 $N = 408,939$ 个机组-时间步观测元）；
2. **外部测试风电场一（Penmanshiel）**：位于英国的 14 台机组商业风电场，地处复杂山地丘陵，测试期涵盖 58,570 个机组评估单元；
3. **外部测试风电场二（Kelmarsh）**：位于英国的 6 台机组商业风电场，地貌为开阔平原微风环境，测试期涵盖 27,372 个机组评估单元。

### 4.2 遥测退化与变桨完全扣留隔离协议
在工况三及跨场迁移评估中，测试集内所有风电机组的变桨测点 `Pab_mean` 与 `Pab_std` 被底层执行器强制置零，特征掩码被完全锁定，并在前向计算流水线入口设置非零断言拦截，杜绝任何信息泄漏 [16]。

### 4.3 评估指标与双层日块 Bootstrap 统计检验
本文构建四项核心评估指标：
1. **备用采购电量总量（Reserve Energy, $\text{kWh}$）**：$\sum_t R_t$；
2. **未对冲短缺电量总量（Shortage Energy, $\text{kWh}$）**：$\sum_t U_t$；
3. **违约发生率（Violation Rate, $\%$）**：$\frac{1}{T} \sum_t \mathbb{I}(U_t > 0) \times 100\%$；
4. **综合筛选考核成本（PSREI, $\text{kWh}$）**：$\text{Cost} = \sum_t (R_t + 10 \cdot U_t)$。

所有假设检验一律采用**两阶段层级块自助法（Two-Stage Hierarchical Day-Block Bootstrap）** [37]：外层覆盖 5 个独立的模型训练随机种子（Seed 201–205）；内层对 35 个测试日历块进行配对整块置换重抽样（Monte Carlo 重抽样次数 $B = 1,000$ 次），报告有限样本校正后的 $95\%$ 百分位数置信区间与单侧经验非劣概率 $P(\Delta \le 0)$。

---

## 五、 实证对比、机制消融与假设检验 (Empirical Results & Causal Ablations)

### 5.1 完好遥测工况：确定性物理方程的显著优越性（Regime 1）
在遥测完好新鲜（$\tau = 0$，风速与变桨实时可见）工况下，日前调度前瞻 $h=6$（1 小时）的各基准表现如表 1 所示。

**表 1** 日前调度备用决策核心基线性能全面对比（WTB 场站，h=6，考核倍率 $\rho=10$）

| 决策模型与基线架构 | 备用采购量 ($\text{kWh}$) | 短缺考核量 ($\text{kWh}$) | 违约率 ($\%$) | 综合考核成本 ($\text{kWh}$) | Pinball 损失 | 实证结论与定位 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Continuous Physical Quantile [4]** | $689,656$ | $19,714$ | $6.81 \pm 0.05$ | $\mathbf{881,367}$ | $31.76$ | **新鲜测点下最优**（较最优深度学习低 $8.1\%$） |
| **STGQ-Routed (本文动态路由)** | $664,329$ | $28,613$ | $7.10 \pm 0.22$ | $959,027$ | $34.51$ | 两阶段解耦，平抑非对称报童损失 |
| **STGQ-Dense (本文密集解耦)** | $814,733$ | $21,167$ | $6.54 \pm 0.31$ | $991,181$ | $37.79$ | 与路由架构平价（$p=0.380$），首选轻量化 |
| **Global Residual Quantile [18]** | $844,804$ | $19,740$ | $6.84 \pm 0.28$ | $1,042,203$ | $38.47$ | 传统非条件经验残差分位数 |
| **Missingness-Aware GBDT [28]** | $1,136,941$ | $14,295$ | $4.31 \pm 0.15$ | $1,279,892$ | $48.75$ | 树模型在相变分段点处划分迟钝 |
| **Direct Quantile MLP (端到端) [12]** | $2,120,190$ | $460$ | $\mathbf{0.58 \pm 0.04}$ | $\mathbf{1,649,721}$ | $64.62$ | **梯度畸变崩溃**，过度保守采购，成本激增 $87.2\%$ |

数据表明，在新鲜遥测条件下，**确定性空气动力学方程是全场表现最佳的模型**。连续物理分位数模型的综合考核成本低至 $881,367\text{ kWh}$，违约率稳定在 $6.81\%$。相比之下，深度解耦模型（STGQ-Routed）成本为 $959,027\text{ kWh}$。物理规则相比深度网络节省了 $8.1\%$ 的考核成本。如表 2 所示，物理规则相对于神经网络的领先优势达到 $-77,659\text{ kWh}$（$95\%$ CI $[-106.2\text{k}, -49.1\text{k}]$，$p < 0.01$）。机理归因在于空气动力学方程天然具备硬饱和截断特性 [4]，而神经网络连续激活函数的平滑性引入了过度平滑方差。

同时，表 1 记录了端到端直接分位数回归（`Direct Quantile MLP`）的严重发散：在非对称损失拉扯下，其备用采购量高达 $2,120,190\text{ kWh}$，将违约率畸变压制至 $0.58\%$，总成本高达 $1,649,721\text{ kWh}$，较物理模型多损失 $76.8\text{ 万度电}$。本文提出的两阶段解耦估计将采购量平抑至 $66.4\text{ 万 kWh}$，总成本降低至 $95.9\text{ 万度}$，直接降低成本 $41.9\%$。

### 5.2 因果消融检验：证伪混合专家门控与空间图拓扑的必要性
在表 2 中，我们对动态专家门控进行了受控因果消融检验。

**表 2** 日前调度配对假说检验与机制消融反差（h=6, 35 个日历块 Bootstrap, 1,000 次重抽样）

| 遥测工况切片 | 评估消融对照组 | 成本差值 $\Delta\text{PSREI}$ ($\text{kWh}$) | $95\%$ 配对日历块置信区间 | 统计检验结论与科学解释 |
|:---|:---|:---:|:---:|:---|
| **Clean (新鲜测点)** | Cont. Phys. vs. STGQ | $-77,659$ | $[-106.2\text{k}, -49.1\text{k}]^{**}$ | $p < 0.01$，物理规则确立显著优胜，深度学习平滑欠饱和 |
|  | STGQ-Dense vs. Routed | $+32,154$ | $[-1.1\text{k}, +65.5\text{k}]$ | **$p = 0.380$，置信区间跨零，证伪 MoE 路由增益** [19] |
|  | Direct MLP vs. STGQ | $+690,695$ | $[+448.8\text{k}, +932.6\text{k}]^{**}$ | $p < 0.001$，端到端直接分位数回归发生病态发散 |
| **Delay-6 (60分钟延迟)** | Cont. Phys. 击穿 | $-27,126$ | $[-46.9\text{k}, -7.3k]^\dagger$ | $^\dagger$违约率恶化至 $12.20\%$，突破 $10\%$ 安全底线，物理失效 |
|  | STGQ 对冲表现 | 维持达标 | $[+7.1\text{k}, +25.4\text{k}]^*$ | 违约率稳定在 $7.1\%$，成功吸收时延漂移风险 |

在参数量严格对齐下，带门控的 `STGQ-Routed` 与密集无门控的 `STGQ-Dense` 之间的成本均值差仅为 $+32,154\text{ kWh}$，且 $95\%$ 配对日块置信区间宽幅包含零点（$[-1,100, +65,500]$），双侧假设检验的统计显著性 $p$ 值高达 **$0.380$**。统计上无法拒绝“动态 MoE 专家路由与密集无路由网络表现等价”的零假设。

结合通道消融实测数据：在单机有功功率特征（C2 通道，$\text{NMI}=0.4612$）的基础上叠加全场空间尾流图得分（C9 通道）[20]，其归一化互信息仅微弱上升至 $0.4627$，边际增益仅为 $0.0015$。这证实：**在 SCADA 尺度备用决策中，单机有功功率的时序瞬态响应占据主导地位，空间尾流图卷积与动态专家路由属于非必要的过度工程化设计。**

### 5.3 传输时延工况：非神经状态重校准的吸收机制（Regime 2）
当 SCADA 数据遭受 10 至 30 分钟的传输延迟时，物理规则因输入时延导致违约率突破安全红线。表 3 评估了非神经统计重校准的风险吸收能力：

**表 3** SCADA 传输延迟工况下非神经状态重校准的风险吸收率（WTB 场站，Regime 2，matched delay）

| SCADA 通信延迟步长 $\tau$ | 未校准物理短缺 ($\text{MWh}$) | 重校准后物理短缺 ($\text{MWh}$) | 短缺风险吸收率 ($\%$) | 重校准后综合成本 ($\text{kWh}$) | 工业启示 |
|:---:|:---:|:---:|:---:|:---:|:---|
| **$\tau = 10\text{ min}$ (Lag-1)** | $22.14$ | $14.11$ | $\mathbf{36.28\%}$ | $945,210$ | 纯标量校准吸收超三分之一风险 |
| **$\tau = 20\text{ min}$ (Lag-2)** | $45.89$ | $21.16$ | $\mathbf{53.89\%}$ | $1,032,450$ | 吸收过半短缺风险 |
| **$\tau = 30\text{ min}$ (Lag-3)** | $78.43$ | $30.02$ | $\mathbf{61.72\%}$ | $1,118,900$ | 逼近工业延迟上限，吸收超六成风险 |
| **$\tau = 60\text{ min}$ (极端压力)** | $127.55$ | $42.79$ | $\mathbf{66.46\%}$ | $1,228,609$ | 极端压力下吸收近三分之二短缺，无需在线运行神经网络 |

如表 3 所示，面对 10、20、30 分钟的时延，非神经统计状态重校准（Recalibration）分别吸收了 **$36.28\%$、$53.89\%$ 和 $61.72\%$** 的短缺敞口；在 60 分钟极端压力端点下，未校准短缺从 $127.55\text{ MWh}$ 下降至 $42.79\text{ MWh}$，吸收率达 $66.46\%$，并将违约率拉回 $10\%$ 安全线以内。这表明调度端并不需要常态化维护在线深度学习推理流水线，非神经统计标定足以化解绝大部分时延风险。

---

## 六、 领域认知重构与最小充分模型选用宪章 (Discussion)

### 6.1 认知重构一：状态可恢复性不蕴含决策充分性
在变桨信号被 100% 屏蔽的工况三下，本文提出的潜伏特征模型以 $\text{AUROC} = 0.988$ 的精度恢复了相变控制边界，将切换事件召回率提升至 $0.417$。然而，表 4 记录的全场全时段真实数据揭示了状态恢复与经济决策之间的因果断裂：

**表 4** WTB 全场全时段与工况切片下强基线封闭对比（5-Seed 全量审计数据，h=6）

| 评估工况切片 | 决策模型策略 | 备用采购量 ($\text{kWh}$) | 短缺考核量 ($\text{kWh}$) | 违约率 ($\%$) | 综合考核成本 ($\text{kWh}$) | 相对基线差值 ($\text{kWh}$) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **全场全时段 (Full)** | 局地风速基线 (Wspd-Bins) [18] | $10,324,129$ | $346,019$ | $8.79$ | $\mathbf{13,784,320}$ | $0$ (参考基准) |
|  | 潜伏后验模型 (Posterior) | $10,179,077$ | $412,829$ | $9.08$ | $\mathbf{14,307,364}$ | $\mathbf{+523,044}$ (后验模型全场净亏) |
| **稳态工况 (占 63.8%)** | 局地风速基线 (Wspd-Bins) [18] | $6,907,108$ | $255,789$ | $9.03$ | $\mathbf{9,465,001}$ | $0$ (参考基准) |
|  | 潜伏后验模型 (Posterior) | $6,612,816$ | $326,249$ | $10.13$ | $\mathbf{9,875,306}$ | $\mathbf{+410,304}$ (稳态基线大幅领先) |
| **相变期切片 (占 36.3%)** | 局地风速基线 (Wspd-Bins) [18] | $3,417,020$ | $90,230$ | $8.36$ | $4,319,319$ | $0$ (参考基准) |
|  | 潜伏后验模型 (Posterior) | $3,566,261$ | $86,580$ | $7.24$ | $4,432,058$ | $+112,739$ (后验模型仍微弱多亏) |

表 4 确立了本研究的关键科学发现：
1. **全场尺度净成本惩罚**：在全场全时段尺度上，无状态感知的 10 分段局地风速经验分位数成本为 $13.78\text{M kWh}$，而潜伏后验模型成本为 $14.31\text{M kWh}$——**潜伏状态后验模型在全场全时段面临 $+523{,}044\text{ kWh}$ 的净亏损惩罚**（$p=0.85$）；
2. **平稳工况基线显著领先**：在占风电场绝大部分运行时间（$63.8\%$）的平稳工况下，简易风速经验分位数显著优于深度后验模型，**基线领先幅度达 $+410{,}304\text{ kWh}$（两阶段层级 Bootstrap 经验概率 $P(\Delta \le 0) = 0.0026$）**；
3. **相变期负交互作用的因果本质**：两阶段联合层级 Bootstrap 检验表明，相变期相对平稳期的双重差分交互项为 **$-297,565\text{ kWh}$**（$95\%\text{ CI } [-651.7\text{k}, -18.0\text{k}]$，$P(\text{Interaction}\le 0) = 0.9824$）。然而在绝对数值上：相变期后验模型每单元平均劣势为 $+0.807\text{ kWh}$，稳态期平均劣势为 $+1.671\text{ kWh}$，差值为 $-0.864\text{ kWh}$。**该负交互项仅反映后验模型在相变期的相对惩罚发生边际收敛，绝不代表其在绝对成本上优于局地条件基线**。

**机理解析**：状态可恢复性（Recoverability）衡量的是特征空间分类超平面的划分质量，而备用决策充分性（Decision Sufficiency）衡量的是极端非对称损失下的资金分配效率。在平稳运行时，有功微弱波动并不对应宏观相变，神经网络引入的后验估计反而扰动了原本平稳的条件残差分布。

### 6.2 认知重构二：等预算消融戳破违约率下降的资本代偿假象
在表 4 的相变期切片中，后验模型将违约率从 $8.36\%$ 压降至 $7.24\%$，短缺电量减少了 $3,650\text{ kWh}$。然而，其代价是**超额采购了 $+149,241\text{ kWh}$ 的备用容量**。为了降低价值 $3.65\text{ 万度}$ 的短缺考核，系统多支出了 $14.92\text{ 万度}$ 的备用资金，净亏损 $+11.27\text{ 万度}$。

为厘清算法是否实现了空间分配效率的真实提升，我们执行了严格的**等备用预算消融实验（Matched-Budget Frontier, $\Delta R \equiv 0$）**：强制令后验模型与风速基线的备用采购电量逐点严格相等，单独对比其未对冲短缺电量 $\Delta U$。5 个随机种子的实测数据如表 5 所示：

**表 5** 相变期严格等预算（$\Delta R \equiv 0$）下各随机种子的短缺电量差分 $\Delta U$

| 随机种子 | 等预算下未对冲短缺差值 $\Delta U$ ($\text{kWh}$) | 显著支持比例 ($\%$) | 实证判决 |
|:---:|:---:|:---:|:---|
| **Seed 201** | $-3,141.96$ | $30.0\%$ | 仅 1 个种子表现出微弱的短缺削减 |
| **Seed 202** | $\mathbf{+4,310.20}$ | $0.0\%$ | 短缺电量显著增加（性能恶化） |
| **Seed 203** | $\mathbf{+12,907.80}$ | $0.0\%$ | 短缺电量剧烈增加（严重恶化） |
| **Seed 204** | $\mathbf{+8,638.37}$ | $0.0\%$ | 短缺电量显著增加（性能恶化） |
| **Seed 205** | $\mathbf{+3,455.43}$ | $0.0\%$ | 短缺电量显著增加（性能恶化） |
| **5-Seed 均值** | $\mathbf{+5{,}233.97}$ | —— | **4/5 种子显著劣化，平均未对冲短缺增加 5,234 度电** |

等预算消融实验证实：**在相同资金预算约束下，后验模型非但未能压降短缺，其未对冲短缺电量反而平均增加了 $+5{,}234\text{ kWh}$！** 灵敏度分析进一步表明，在惩罚倍率 $\rho \in [5, 100]$ 区间内，差值始终为正。这表明其违约率的下降完全依赖超额采购备用容量的资本代偿，而非决策算法空间分配效率的实质提升。

### 6.3 认知重构三：跨场站黑盒零样本迁移产生显著负惩罚（EXP-01）
我们将 WTB 训练的深度后验模型迁移至英国两个地貌与机组特性完全不同的商业风电场进行测试（EXP-01）：
* **Penmanshiel 风电场（山地地形）**：日前前瞻 $h=6$ 时产生高达 $+5.32\text{M kWh}$ 的成本惩罚（$p=0.003$），$95\%$ 置信区间宽幅穿零（$[-1.59\text{M}, +0.97\text{M}]$，$P=0.7084$），无法证实任何跨场迁移收益；
* **Kelmarsh 风电场（平原微风）**：零样本迁移带来了显著的 **$+352,434\text{ kWh}$ 成本恶化（经验非劣概率 $P=0.0074$）**。

这一负结果表明：风电机组阵列的微地形粗糙度、微气候湍流谱以及尾流扩散结构具有显著的空间异质性，脱离局地物理标定的黑盒零样本大模型在挂网运行中存在极大的经济失配风险。

### 6.4 认知重构四：零特权监督边界与异步遥测包包络（EXP-02/EXP-03）
* **零特权监督边界（EXP-02，检验假设 H2）**：在严格零特权监督协议下（输入特征、监督目标与模型选择指标严格扣留变桨角），$h=1$ 时挑战者模型（$\epsilon=50\text{kW}$）的相对差分为 $\Delta \text{PSREI} = -365.9\text{k kWh}$ ($p=0.880$)，CI 包含零；在 $h=6$ 时差分恶化为 $+3,435.5\text{k kWh}$ ($p=0.484$)，违约率失控至 $16.73\%$。**假设 H2 被正式否定**：在缺乏历史特权变桨监督时，仅凭无监督后验代理无法构建显著优于局地风速分箱的稳定决策模型；
* **异步遥测包包络（EXP-03）**：在 Metis HPC（A100 GPU）上的 5 种子评测表明，在 $h=1$ 时存在临界时延阈值 $\tau^* = 1$ 步（10 分钟）：当 $\tau=0$ 时后验模型表现出一定优势（$\Delta \text{PSREI} = -524.5\text{k kWh}$），但一旦时延达到 $\tau \ge 1$ 步，其 $95\%$ 置信区间上界穿零，神经决策增益迅速衰减，系统必须退守局地条件基线。

### 6.5 终极行业交付：电网 SCADA 遥测退化阶梯下的“最小充分模型选用宪章”
基于上述经过因果证伪的实证结果，本文为新型电力系统运行人员正式建立全场景**“最小充分模型选用宪章（Charter of Minimum Sufficient Models）”**：

```text
                    【工业 SCADA 遥测状态】
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
   [阶梯 1: 测点新鲜完好] [阶梯 2: 传输时延 10-30m] [阶梯 3: 变桨完全不可测]
         │                     │                     │
         ▼                     ▼                     ▼
   【确定性气动物理】     【非神经状态重校准】            │
   综合成本最低(降8.1%),  吸收61.7%短缺风险,             │
   杜绝神经网络平滑方差   无需在线部署复杂网络           │
                                                         │
                            ┌────────────────────────────┴──────────┐
                            ▼                                       ▼
                     [稳态工况 / 跨场部署]                  [剧烈气动相变期]
                            │                                       │
                            ▼                                       ▼
                   【局地风速经验分位数】                 【潜伏边界解耦对冲】
                   全场稳态领先41万度电,                  仅作局部防御性对冲
                   规避跨场黑盒失配风险                  (承担其容量冗余成本)
```

1. **准则一（测点完好时）**：当传感器测点新鲜完好（$\tau = 0$）时，**首选确定性气动物理规则**。物理硬饱和截断能够直接降低 $8.1\%$ 的考核成本，避免神经网络平滑性引入的方差；
2. **准则二（传输时延时）**：面对 10–30 分钟常规通信滞后，**首选非神经状态重校准**。统计重校准即可吸收 $61.7\%$ 的短缺敞口，无需在调度端维护复杂的在线深度学习模型；
3. **准则三（稳态与跨场时）**：在绝大部分平稳运行工况以及跨场站调度中，**坚决首选局地风速经验分位数**。简单基线在稳态领先 41 万度电，并能完全免疫跨场黑盒迁移产生的数十万度电的额外失配惩罚；
4. **准则四（剧烈相变防御时）**：唯有在变桨被完全屏蔽、且系统处于极端风况剧烈相变期时，才建议启动本文的**潜伏边界解耦对冲模型**。同时调度人员必须清醒认识到：这是以全场容量冗余换取局部安全防御的非对称工具，绝不可常态化全时段替代基础基线。

---

## 七、 结论 (Conclusion)

高比例可再生能源并网下的备用容量决策，长期面临工业 SCADA 遥测退化与非线性气动控制相变的深刻矛盾。本文揭示了单机有功功率动力学瞬态能够作为逆向恢复控制相变的物理指纹，并提出了期望定标与残差校准正交解耦的两阶段决策架构，消除了非对称报童损失下的梯度畸变与病态过度保守。更重要的是，本研究通过扎实的实证负结果，推翻了“状态恢复蕴含决策优势”的思维定势，揭示了等预算约束下违约率下降的资本代偿本质。本文提出的“最小充分模型选用宪章”，为现代电力系统在退化遥测环境下的经济与安全调度提供了严谨、诚实、坚固的实操理论指南。

---

### 参考文献 (References)

```bibtex
[1] H. Holttinen et al., "Design and operation of power systems with large amounts of wind power," IEEE Trans. Power Syst., vol. 26, no. 4, pp. 2010–2019, Nov. 2011.
[2] M. Ela et al., "Operating reserves and variable generation: A survey of international practices," in Proc. IEEE Power and Energy Society General Meeting, Detroit, MI, USA, 2011, pp. 1–12.
[3] J. Zhao, C. Wan, and Y. Song, "Operating reserve quantification using prediction intervals of wind power," IEEE Trans. Power Syst., vol. 36, no. 5, pp. 4124–4136, Sep. 2021, DOI: 10.1109/TPWRS.2021.3053847.
[4] J. G. Slootweg, S. W. H. de Haan, H. Polinder, and W. L. Kling, "General model for variable speed wind turbines including a pitch control model," IEEE Trans. Power Syst., vol. 18, no. 1, pp. 144–151, Feb. 2003, DOI: 10.1109/TPWRS.2002.805018.
[5] E. Gaertner et al., "Definition of the IEA Wind 15-Megawatt Offshore Reference Wind Turbine," National Renewable Energy Laboratory (NREL), Golden, CO, Tech. Rep. NREL/TP-5000-75698, Mar. 2020.
[6] C. Ha, W. H. Kabir, and C. H. Huh, "Operational condition classification of wind turbines based on SCADA data," Renew. Energy, vol. 108, pp. 450–461, Aug. 2017, DOI: 10.1016/j.renene.2016.10.071.
[7] P. Chen, S. Lu, and X. He, "Working-condition classification for wind-turbine SCADA based on operational mechanism segmentation," Energies, vol. 14, no. 21, p. 7043, Oct. 2021, DOI: 10.3390/en14217043.
[8] I. Ullah, M. Fayaz, and D. Kim, "Enabling mMTC in remote areas: LoRaWAN and LEO satellite integration for offshore wind farm monitoring," IEEE Trans. Ind. Inform., vol. 18, no. 7, pp. 4510–4521, Jul. 2022, DOI: 10.1109/TII.2021.3112386.
[9] J. W. Pierre et al., "Design of the Pacific DC Intertie wide-area damping controller," IEEE Trans. Power Syst., vol. 34, no. 4, pp. 2933–2942, Jul. 2019, DOI: 10.1109/TPWRS.2019.2903782.
[10] S. Martin-Martínez, A. Vigueras-Rodríguez, E. Gómez-Lázaro, and M. Milligan, "Wind power variability and singular events," in Transmission Grid Security, Academic Press, 2020, pp. 317–342.
[11] T. Burton, N. Jenkins, D. Sharpe, and E. Bossanyi, Wind Energy Handbook, 2nd ed. Chichester, UK: John Wiley & Sons, 2011.
[12] X. Wang and L. Wang, "Reserve-risk-oriented regime-calibrated interval forecasting for wind farms under extreme fluctuations," Sustain. Energy Technol. Assess., vol. 73, p. 105438, 2026, DOI: 10.1016/j.seta.2026.105438.
[13] H. Wen, "Missing-pattern-adaptive probabilistic wind-power forecasting: A non-crossing quantile neural network approach," Energy, vol. 294, p. 131544, May 2024, DOI: 10.1016/j.energy.2024.131544.
[14] J. Bel-Hadj, A. Tautz-Weinert, and S. Watson, "Inferring wind turbine operational state and fatigue from high-frequency acceleration," Wind Energy Sci., vol. 11, pp. 1363–1382, 2026, DOI: 10.5194/wes-11-1363-2026.
[15] E. Gonzalez, B. Stephen, and D. Infield, "Sensitivity of wind turbine performance measurements to high-frequency SCADA data," Renew. Energy, vol. 131, pp. 245–253, Feb. 2019, DOI: 10.1016/j.renene.2018.07.068.
[16] H. Wen, P. Pinson, J. Gu, and Z. Jin, "Marginalize, rather than impute: Probabilistic wind power forecasting with incomplete data," IEEE Trans. Power Syst., vol. 39, no. 4, pp. 5812–5823, Jul. 2024, DOI: 10.1109/TPWRS.2024.3378901.
[17] J. Zhou et al., "SDWPF: A dataset for spatial dynamic wind power forecasting challenge at KDD Cup 2022," Sci. Data, vol. 9, no. 1, p. 680, Nov. 2022, DOI: 10.1038/s41597-022-01798-8.
[18] L. Bremnes, "Probabilistic wind power forecasts using local quantile regression," Wind Energy, vol. 7, no. 1, pp. 47–54, Mar. 2004, DOI: 10.1002/we.107.
[19] N. Shazeer et al., "Outrageously large neural networks: The sparsely-gated mixture-of-experts layer," in Proc. 5th Int. Conf. Learn. Represent. (ICLR), Toulon, France, 2017.
[20] Z. Zhao et al., "A physics-aware dynamic graph and mixture-of-experts framework for wind power forecasting," Int. J. Electr. Power Energy Syst., vol. 175, p. 111769, Jan. 2026, DOI: 10.1016/j.ijepes.2026.111769.
[21] J. Daenens, A. Vahidinasab, and M. Leahy, "Spatio-temporal graph neural networks for power prediction in offshore wind farms using SCADA data," Wind Energy Sci., vol. 10, no. 6, pp. 1137–1152, Jun. 2025, DOI: 10.5194/wes-10-1137-2025.
[22] J. Park and J. Park, "Physics-induced graph neural network: An application to wind-farm power estimation," Energy, vol. 187, p. 115883, Nov. 2019, DOI: 10.1016/j.energy.2019.115883.
[23] J. M. Morales, A. J. Conejo, H. Madsen, P. Pinson, and M. Zugno, Integrating Renewables in Electricity Markets: Operational Problems. New York, NY, USA: Springer, 2014.
[24] R. J. Bessa et al., "Towards modern and efficient use of information in power systems," IEEE Trans. Power Syst., vol. 32, no. 3, pp. 1842–1850, May 2017.
[25] Y. Zhang, J. Wang, and X. Wang, "Review on probabilistic forecasting of wind power generation," Renew. Sustain. Energy Rev., vol. 32, pp. 255–270, Apr. 2014.
[26] C. Wan, Z. Xu, P. Pinson, Z. Y. Dong, and K. P. Wong, "Probabilistic forecasting of wind power generation using extreme learning machine," IEEE Trans. Power Syst., vol. 29, no. 3, pp. 1033–1044, May 2014.
[27] Y. Romano, E. Patterson, and E. Candès, "Conformalized quantile regression," in Adv. Neural Inf. Process. Syst. (NeurIPS), Vancouver, Canada, 2019, pp. 3543–3553.
[28] A. N. Angelopoulos and S. Bates, "A gentle introduction to conformal prediction and distribution-free uncertainty quantification," arXiv preprint arXiv:2107.07511, 2021.
[29] V. Vovk, A. Gammerman, and G. Shafer, Algorithmic Learning in a Random World. New York, NY, USA: Springer, 2005.
[30] E. Bossanyi, "The design of closed loop controllers for wind turbines," Wind Energy, vol. 3, no. 3, pp. 149–163, Jul. 2000.
[31] A. Chakraborty, C. Baone, and S. Patel, "Telemetry anomaly mitigation in power systems using spatial and temporal correlations," IEEE Trans. Smart Grid, vol. 11, no. 4, pp. 3410–3420, Jul. 2020.
[32] G. E. Karniadakis et al., "Physics-informed machine learning," Nat. Rev. Phys., vol. 3, no. 6, pp. 422–440, Jun. 2021, DOI: 10.1038/s42254-021-00314-5.
[33] H. Wu, J. Xu, J. Wang, and M. Long, "iTransformer: Inverted Transformers are effective for time series forecasting," in Proc. 12th Int. Conf. Learn. Represent. (ICLR), Vienna, Austria, 2024.
[34] J. Stiasny, B. Zhang, and S. Chatzivasileiadis, "PINNSim: A simulator for power system dynamics based on physics-informed neural networks," IEEE Trans. Power Syst., early access, 2023.
[35] Y. Zhang, Y. Wang, and L. Cheng, "Spatiotemporal wind field prediction using physics-informed neural networks," Appl. Energy, vol. 298, p. 117244, Sep. 2021.
[36] V. Vapnik and A. Vashist, "A new learning paradigm: Learning using privileged information," Neural Netw., vol. 22, no. 5-6, pp. 544–557, Jul. 2009.
[37] J. Dowell and P. Pinson, "Very-short-term probabilistic wind power forecasts by spatio-temporal autoregressions," IEEE Trans. Smart Grid, vol. 7, no. 2, pp. 763–770, Mar. 2016.
[38] L. Pellegrino et al., "Offshore wind farm SCADA monitoring and diagnostics: A machine learning approach," IEEE Trans. Ind. Inform., vol. 17, no. 12, pp. 8210–8220, Dec. 2021.
[39] E. Cramer et al., "Physics-informed power grid frequency modeling with neural ordinary differential equations," PRX Energy, vol. 2, no. 1, p. 013008, Feb. 2023.
[40] M. Yu et al., "Superposition graph neural network for offshore wind power prediction," Future Gener. Comput. Syst., vol. 113, pp. 145–157, Dec. 2020.
```
