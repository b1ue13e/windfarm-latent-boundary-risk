# 论文可复现性指南与开放科学声明 (Reproducibility & Open Science Protocol)

**对应论文**：《潜伏控制相变与遥测退化约束下的风电运行备用决策：最小充分模型准则》  
**对应工件**：Table 1 ~ Table 4, Figure 1 ~ Figure 6, Equations (1) ~ (15)

---

## 一、 计算环境与软件依赖

### 1.1 硬件与操作系统环境
* **操作系统**：Windows 11 Enterprise (x64) / Ubuntu 22.04 LTS (x86_64)
* **计算架构**：AMD Ryzen / Intel Xeon CPU，NVIDIA GeForce RTX 4090 (24GB VRAM) / A100 (80GB VRAM)
* **CUDA 版本**：CUDA 12.1 / cuDNN 8.9.2

### 1.2 Python 核心依赖库
```bash
python >= 3.10
torch == 2.2.0+cu121
numpy == 1.26.4
pandas == 2.2.1
scipy == 1.12.0
scikit-learn == 1.4.1.post1
lightgbm == 4.3.0
matplotlib == 3.8.3
seaborn == 0.13.2
python-docx == 1.1.0
latex2mathml == 3.77.0
lxml == 5.1.0
```

---

## 二、 实验数据源与评估单元规格

1. **主源场站（SDWPF 官方商业风电场基准）**：
   * **场站规格**：134 台 1.5 MW 双馈风电机组（DFIG），全场总额定容量 201 MW；
   * **采样频率**：10 分钟 SCADA 时间序列；
   * **测试集周期**：严格选定跨越完整气象周期的 35 个连续日历日（共计 $35 \times 144 = 5,040$ 个离散时步）；
   * **评估单元总数**：$N = 408,939$ 个机组时步样本；
   * **工况屏蔽测试**：在工况三（变桨物理屏蔽）下切除变桨测点并在特征流水线设置非零断言拦截；在工况二（传输时延）下设置因果队列缓冲区模拟量测滞后 10 至 60 分钟。
2. **外部迁移场站（英国真实商业风电场）**：
   * **Penmanshiel 场站**：丘陵山地地貌，14 台机组，58,570 个评估单元；
   * **Kelmarsh 场站**：开阔平原地貌，6 台机组，27,372 个评估单元。

---

## 三、 随机种子与统计显著性检验协议

* **随机种子列表**：Seed 201, Seed 202, Seed 203, Seed 204, Seed 205
* **统计抽样方法**：双层日历块自助法（Hierarchical Day-Block Bootstrap）：
  * 第一层：在 5 个随机种子间保持配对；
  * 第二层：在 35 个整日历块（每日 144 个 10 分钟时步）间进行 $B=1,000$ 次配对置换重抽样；
  * 输出统计量：95% 经验置信区间（Empirical CI）与单侧非劣概率 $P(\Delta \le 0)$。

---

## 四、 核心实验与图表一键复现指令

### 4.1 核心基准对比（表 1 与表 2）
```powershell
# 运行主场站 WTB 全量基准评测（包含物理模型、端到端 MLP、GBDT、无状态经验分位数与 STGQ 架构）
python scripts/train_capacity_matched_dense_wtb.py --seeds 201 202 203 204 205 --horizon 6 --rho 10
# 生成表 1 核心评测指标与置信区间
python scripts/build_statistical_claim_table.py
```

### 4.2 传输时延与状态重校准消融（表 2）
```powershell
# 评估 10 min、20 min、30 min、60 min 时延下非神经标量重校准风险吸收率
python scripts/eval_markov_gilbert_telemetry.py --tau 10 20 30 60
```

### 4.3 全场时段与相变过渡期消融（表 3 与表 4）
```powershell
# 运行稳态工况（63.8%）与相变过渡期（36.3%）双重差分与等预算约束消融
python scripts/build_reserve_claim_boundary_table.py --matched-budget
```

### 4.4 论文 6 大高清矢量图表生成
```powershell
# 生成图 1：遥测退化阶梯与两阶段正交优化解耦架构图
python scripts/generate_figure1.py
# 导出图 2 至图 6 高清图表
python scripts/plot_phase_and_abstention.py
python scripts/plot_rmse_vs_reserve_risk.py
```

### 4.5 编译输出出版级 Word 文档与 XeLaTeX PDF
```powershell
# 生成完整 Word 文档（嵌入全部 15 个原生 OMML 公式、84 个行内公式、6 幅图表与 4 张三线表）
python scripts/make_topjournal_word.py

# 编译生成 12 页学报双栏 PDF
cd build
xelatex -interaction=nonstopmode paper_chinese_topjournal.tex
xelatex -interaction=nonstopmode paper_chinese_topjournal.tex
cd ..
Copy-Item build/paper_chinese_topjournal.pdf "manuscript/论文_潜伏控制相变与遥测退化约束下的风电运行备用决策_最小充分模型准则.pdf" -Force
```

---

## 五、 数据完整性与哈希校验

所有主测试集与模型输出均通过 SHA-256 校验确保无数据篡改或选择性报告：
* 验证门禁命令：`python .agents/scripts/verify_gate.py`
* 门禁判定：`VERIFICATION_GATE: PASS`
