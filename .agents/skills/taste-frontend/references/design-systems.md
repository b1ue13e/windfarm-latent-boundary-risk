# 官方设计系统选型与技术规范 (Design Systems Map)

在确定了页面的 `Design Read` 之后，必须挑选最合适的设计系统底座。**严禁为已有官方成熟包的组件手工拼凑生硬的 CSS，也严禁将某种纯审美趋势冒充为官方系统。**

---

## 1. 场景 → 官方设计系统选型矩阵

当需求明确契合以下场景时，请直接引入并使用对应的**官方组件与设计令牌 (Tokens)**：

| 需求意图 (Brief Reads As...) | 推荐官方技术栈 / 设计系统 | 选型理由与核心优势 |
|---|---|---|
| **微软生态 / 企业级 SaaS / 密集工作台** | `@fluentui/react-components` 或 `@fluentui/web-components` | 微软官方 Fluent 2 设计系统，内置完善的无障碍与工作流交互支持 |
| **Google 生态 / Material 原生产品** | `@material/web` + Material 3 Tokens | Google 官方 M3 标准，具备强大的动态配色系统与 Android 亲和力 |
| **IBM 风格 / B2B 工业级数据分析** | `@carbon/react` + `@carbon/styles` | IBM Carbon 设计系统，成熟的高密度网格排版与数据看板模式 |
| **Shopify 生态 / 电商卖家后台** | `@shopify/polaris` 或 Web Components | Shopify 官方标准，商家端界面必备规范 |
| **Atlassian / Jira 协同类产品** | `@atlaskit/*` + `@atlaskit/tokens` | Atlassian 官方设计系统，适合项目管理与流程看板 |
| **GitHub 风格 / 开发者工具与开源主页** | `@primer/react` 或 `@primer/react-brand` | GitHub 官方 Primer 系统；`react-brand` 专用于高质感营销展示 |
| **现代自研 SaaS (自主拥有组件源码)** | **shadcn/ui** (`npx shadcn@latest add ...`) + Tailwind | 源码直出、轻量灵活、无锁定，便于二次深度定制（禁止直接交付默认原始状态） |
| **高可访问性 React 基础原语** | **@radix-ui/themes** 或 `@radix-ui/react-*` | 原语级 Headless 状态管理，搭配精致默认主题与键盘导航支持 |
| **独立团队现代 Web / AI 营销主页** | **Tailwind CSS v4** + 原生 CSS Grid + 语义化组件 | 极致灵活、现代 CSS 特性原生支持、轻巧无冗余 |

### 核心纪律：
1. **真实性原则**：一旦选定上述官方系统，安装并使用官方包与 Token 变量，不要手动凭空伪造。
2. **单一系统原则**：**一个项目只使用一个主设计系统**。严禁在同一棵组件树中将 Material 3、Fluent UI 和 Carbon 混杂在一起。

---

## 2. 纯审美流派的真实实现原则 (Aesthetic Directions)

对于以下纯视觉风格流派，**没有唯一的单一官方包**。必须基于原生 CSS + Tailwind CSS + 无障碍 Headless 原语进行诚实实现：

| 审美流派 | 诚实工程实现方案 | 关键实现要点 |
|---|---|---|
| **玻璃拟态 (Glassmorphism)** | `backdrop-filter: blur(...)` + 1px 双层高光边框 | 必须为 `prefers-reduced-transparency` 提供纯色不透明回退降级 |
| **Apple 风格 Bento 网格** | 原生 CSS Grid (`grid-template-columns`) | 采用非对称单元格尺寸（如 2:1、1:2、全宽跨行），严禁生硬堆砌等宽卡片 |
| **极简杂志风 (Editorial)** | 高反差 Serif 大标题 + 几何无衬线正文 | 大量负空间留白、严谨的 65ch 字符行宽控制 |
| **工业粗野主义 (Brutalist)** | 纯直角 (radius 0) + 粗边框 (1-2px) + Monospace | 类似工业机械手册与工程蓝图，以结构线与网格代替阴影 |
| **暗黑极客 (Dark Tech)** | Monospace 代码字体 + 终端视口 + 激光单点亮色 | OLED 级深色底（如 `#09090b`）配合细如发丝的边框 (`border-white/10`) |
| **动效排版 (Kinetic Typography)** | CSS Scroll-Driven Animations / GSAP / Motion | 依托视口进场插值，禁止未经节制的无限死循环跑马灯 |
| **极光 / 网格渐变 (Mesh Gradients)** | 细微径向渐变分层或 SVG 滤镜 | 限制透明度与色彩饱和度，严禁高亮刺眼的杂色霓虹球 |

---

## 3. Tailwind CSS v4 工程最佳实践

Tailwind v4 带来了全新一代基于 CSS 原生的极简配置与更强性能：

1. **导入与配置**：
   - 优先在根 CSS 中使用 `@import "tailwindcss";`。
   - 自定义主题变量使用 `@theme` 块声明：
     ```css
     @import "tailwindcss";

     @theme {
       --font-display: "Geist", system-ui, sans-serif;
       --font-mono: "Geist Mono", monospace;
       --color-brand-accent: #0ea5e9;
     }
     ```
2. **色彩层级映射**：
   - 统一使用中性灰基底：优先选用 `zinc` 或 `neutral`，保持页面冷暖色调的绝对纯粹，不要在同一个组件树里忽冷忽热（例如混用 `slate` 与 `warm-stone`）。
3. **响应式断点**：
   - 严格遵循标准断点 `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`, `2xl: 1536px`。
   - 所有多列布局在 `md`（768px）以下必须显式指定降级为单列。
