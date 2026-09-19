# 📐 任务颗粒度降维交付实战指南 (Stepwise Delivery Workflow)

当工程任务规模较大（如实现一个新的评价指标类、重写整个数据管道、训练脚本）时，**一次性全量生成必然导致模型注意力衰减并引发偷工减料**。

通过本指南提供的“三阶降维交付法”，可确保每一步都在模型的绝对控制力范围之内。

---

## 🔄 三阶段工作流规范

```text
阶段 1: 骨架与接口冻结 (Interface Freeze)
   ↓ (人类审核签名与设计，零试错成本)
阶段 2: 逐模块原子填充 (Atomic Implementation)
   ↓ (每次仅生成 1 个函数，100% 饱满无省略)
阶段 3: 自动化自检与测试 (Verification & Self-Check)
   ↓ (Flash 子智能体并发跑单测与类型检查)
交付完成
```

---

## 🛠️ 实战对话示例

### 阶段 1：骨架与接口冻结 (Prompt 示范)
> **人类向智能体输入**：
> “我们现在需要实现 `MetricCalculator` 模块。**请不要直接写具体实现**，第一步仅输出该模块的类设计、方法签名、参数与返回值类型，以及详细的 docstring。”

* **智能体产出**：
  ```python
  class MetricCalculator:
      """负责自定义评价指标计算的核心类。"""
      
      def __init__(self, p: int, device: str = "cpu") -> None:
          """初始化参数校验与缓存。"""
          ...
      
      def compute_custom_metric_a(self, h: torch.Tensor, targets: torch.Tensor) -> float:
          """计算自定义度量 A Metric_A。"""
          ...
      
      def compute_custom_metric_b(self, centroids: torch.Tensor) -> float:
          """计算自定义度量 B Metric_B。"""
          ...
  ```
* **人类确认**：“接口设计符合规范，进入具体实现。”

---

### 阶段 2：逐模块原子填充 (Prompt 示范)
> **人类向智能体输入**：
> “现在只针对 `compute_custom_metric_a` 方法编写生产级实现。
> 【反偷懒约束】：严禁占位符，写全所有矩阵维度校验、除零防护与 NaN 检测，逐行给出完整实现。”

* **效果**：此时模型把 100% 的生成预算、Working Memory 全部投入到这一个函数中，写出的代码质量、注释丰富度和边界防护达到最高标准。

---

### 阶段 3：自动化测试与闭环验证
> **智能体（主 Pro 领队）调度 Flash 工蚁**：
> 派发 Flash 子智能体生成单测并在命令行运行 `pytest tests/test_custom_metric_a.py`。
> Flash 几秒内跑完单测，若有报错，Flash 提取出错误追踪行号并回传给主 Pro，主 Pro 精准修复。

