---
name: taste-frontend
description: 前端高级审美与反模板化（Anti-Slop）工程规范。用于构建高质感落地页 (Landing Page)、官网、品牌门户、组件库重构、UI 改版与现代 Web 应用。在写代码前强制进行需求意图推断 (Brief Inference)、设定三大控制旋钮 (Variance/Motion/Density)、匹配官方设计系统，严禁 AI 典型模板套路（紫色渐变光、千篇一律的 Inter 字体、固定 3 列卡片、无理由居中 Hero、假截图 div 等），并执行严格的交付前预检闭环。
---

# taste-frontend: 前端高级审美与反模板化工程规范

> 核心定位：拒绝平庸、生硬、拼凑的“AI 模板味”前端代码。无论构建何种 Web 界面，每一项设计决策必须基于上下文需求，严守排版、色彩、间距、动效与响应式的工程纪律。

---

## 0. 需求意图推断 (Brief Inference)

在写任何一行代码或调整样式前，**必须先研判用户的真实意图与上下文场景**。绝大多数 AI 生成的前端之所以糟糕，是因为模型直接跳入了一套刻板印象的默认样式。

### 0.A 核心信号研判
1. **页面类型 (Page Kind)**：
   - 商业 SaaS / 开发者工具 / 消费级品牌 / 创意机构 / 活动发布 / 个人作品集 / 编辑部杂志 / 企业级后台。
2. **风格关键词 (Vibe Words)**：
   - "极简 (minimalist)"、"克制沉静 (calm)"、"Linear 风格"、"Apple 质感"、"Awwwards 级"、"工业粗野 (brutalist)"、"高端杂志 (editorial)"、"暗黑极客 (dark tech)" 等。
3. **目标受众 (Audience)**：
   - B2B 采购决策者 / 极客开发者 / 注重品味的普通消费者 / 审阅作品集的 HR 或设计总监。受众决定审美取向，而非模型的个人偏好。
4. **既有品牌资产 (Brand Assets)**：
   - 既有 Logo、品牌色、专属字体、实拍素材。在重构场景中，这些是必须继承与尊重的输入。
5. **硬性约束 (Quiet Constraints)**：
   - 无障碍优先 (a11y)、政务/公用事业合规、金融/医疗强信任感、儿童产品。这些约束**绝对优先于**任何艺术修饰。

### 0.B 强制输出单行 "Design Read"
在输出具体代码或实施方案前，必须明确输出一行设计意图研判：
> **`Reading this as: <页面类型> for <目标受众>, with a <风格语汇> language, leaning toward <设计系统或审美流派>.`**

**示例：**
- *`Reading this as: B2B SaaS landing for technical buyers, with a Linear-style minimalist language, leaning toward Tailwind v4 + Geist + restrained motion.`*
- *`Reading this as: creative director portfolio for design agencies, with an editorial / kinetic-type language, leaning toward native CSS + scroll-driven animation + high-contrast typography.`*
- *`Reading this as: redesign of a trust-first health service site, with an accessible calm language, leaning toward Radix UI + cold neutrals + high contrast.`*

### 0.C 模糊意图处理
若需求存在分歧，仅允许提出**一个精准的二选一问题**（严禁发出一长串问卷），例如：*“该页面倾向于更接近 Linear 的克制现代感，还是 Awwwards 的先锋艺术感？”*
若上下文足以自信推断，则**严禁多问**，直接声明 `Design Read` 并推进执行。

### 0.D 绝对禁止的“AI 默认套路” (Anti-Default)
严禁未经审视直接使用以下默认模式：
- 居中 Hero 配合背后紫色/蓝色光晕 (Purple/Blue Glow Mesh)
- 一模一样等宽的 3 列 Feature 卡片
- 满屏生硬的玻璃拟态 (Glassmorphism)
- Inter 字体 + `slate-900` 纯深灰背景
- 无节制的全屏无限循环微动效

---

## 1. 三大核心控制旋钮 (The Three Dials)

在确立 `Design Read` 后，配置三项核心控制参数（取值 1–10）：

* **`DESIGN_VARIANCE: 8`** (1 = 绝对规整对称, 10 = 高度艺术化与非对称张力)
* **`MOTION_INTENSITY: 6`** (1 = 纯静态呈现, 10 = 电影级物理编排与滚动驱动)
* **`VISUAL_DENSITY: 4`** (1 = 艺术画廊般大量留白, 10 = 紧凑仪表盘/数据密集)

**基准默认值：** `8 / 6 / 4`（适用于常规高端 Landing Page / 官网）。

### 旋钮映射推荐表
| 场景信号 | VARIANCE | MOTION | DENSITY |
|---|:---:|:---:|:---:|
| 极简 / 现代克制 / Linear 风格 / 编辑杂志 | 5–6 | 3–4 | 2–3 |
| 高端消费级 / Apple 风格 / 奢品体验 | 7–8 | 5–7 | 3–4 |
| 先锋创意 / Awwwards / 艺术工作室 / 互动实验 | 9–10 | 8–10 | 3–4 |
| 商业 SaaS / 开发者工具营销页 (默认) | 7–9 | 6–8 | 3–5 |
| 严肃公用事业 / 医疗 / 金融信任优先 | 3–4 | 2–3 | 4–5 |
| 既有项目局部重构 (Preserve) | 匹配既有 | +1 | 匹配既有 |
| 既有项目彻底翻新 (Overhaul) | +2 | +2 | 匹配既有 |

---

## 2. 架构与技术栈标准 (Architecture Conventions)

若无特殊指定，默认采用现代前端工业级标准：

### 2.A 技术栈底座
- **框架**：React 19 / Next.js (App Router，默认 RSC)。
  - **RSC 安全隔离**：任何使用 Motion 动效、监听滚动、指针物理交互、Canvas 渲染的组件，必须抽离为带有 `"use client"` 的独立叶子组件，服务端组件仅负责静态骨架与数据渲染。
  - **Vue 3**：使用 `<script setup lang="ts">` + 单向数据流。
- **样式**：**Tailwind CSS v4** (优先) 或 Tailwind v3。
- **动效库**：**Motion**（原 Framer Motion，推荐 `import { motion } from "motion/react"`）与 **GSAP 3** (`gsap` + `ScrollTrigger` 用于复杂钉扎与水平滚动）。
- **字体加载**：强制使用 `next/font` (Next.js) 或本地 `@font-face` + `font-display: swap`，禁止在生产环境直接 `<link>` 阻塞外链。

### 2.B 状态与交互性能底线
- **严禁**在 `useState` 中监听高频连续输入（鼠标坐标、滚动位置 `window.scrollY`、磁吸悬停）。必须使用 Motion 的 `useMotionValue` / `useTransform` / `useScroll` 或 GSAP，避免触发 React 全树重渲染。
- **视口防跳动**：全屏 Hero / Section 强制使用 `min-h-[100dvh]`，**严禁**使用 `h-screen`（避免移动端 Safari 地址栏收缩时产生剧烈布局跳动）。
- **网格优先**：严禁使用复杂的 flexbox 百分比计算 (`w-[calc(33%-1rem)]`)，统一使用原生 CSS Grid (`grid grid-cols-1 md:grid-cols-3 gap-6`)。

### 2.C 图标与符号规范
- **推荐图标库**：`@phosphor-icons/react` (首选)、`hugeicons-react`、`@radix-ui/react-icons`、`@tabler/icons-react`。
- **受控使用**：`lucide-react`（仅在项目既有依赖或用户明确指定时使用）。
- **严禁手绘劣质 SVG**：如果缺少某个图标，安装规范图标包或使用干净几何图元组合，禁止手搓杂乱的 SVG Path。
- **全站统一**：一个项目内只允许使用**一套**图标家族，全局统一 `strokeWidth`（如统一为 `1.5` 或 `2.0`）。
- **Emoji 禁令**：默认禁止在专业 UI、标题、正文与标注中乱插 Emoji。仅在明确要求“社交娱乐/聊天”风格时克制使用。

---

## 3. 设计工程硬性纪律 (Design Engineering Directives)

### 3.1 排版纪律 (Typography)
- **字体选型**：
  - 严禁把 `Inter` 作为无脑默认无衬线字体。优先选用更有性格的现代无衬线：`Geist`、`Outfit`、`Cabinet Grotesk`、`Satoshi`。
  - 衬线体 (Serif) 极其克制：严禁将 `Fraunces`、`Instrument Serif` 作为通用的 AI 默认衬线。仅在明确为文学/高端奢侈/编辑出版类场景下，从推荐池挑选（如 `PP Editorial New`, `Tiempos Headline`, `Playfair Display`, `Cormorant Garamond`）。
- **斜体下行字母间隙保护 (Italic Descender Clearance)**：
  - 当在大号 Display 字体中使用斜体且包含下行字母（`y`, `g`, `j`, `p`, `q`）时，`leading-none` 会裁剪字母底部。必须使用 `leading-[1.1]` 并为容器预留 `pb-1` 或 `mb-1`。
- **字号与行高阶梯**：
  - 大标题 (Display/H1)：`text-4xl md:text-6xl lg:text-7xl tracking-tighter leading-[1.05]`。
  - 正文 (Body)：`text-base md:text-lg text-muted leading-relaxed max-w-[65ch]`，严格限制行宽不超过 65 个字符。

### 3.2 色彩标定 (Color Calibration)
- **单强调色原则**：全站最多设定 **1 个** 主强调色，饱和度默认控制在 **80% 以下**。
- **严禁“AI 紫光” (Lila Glow)**：严禁在深色背景上无脑使用紫色光晕、霓虹边缘。推荐采用纯净的中性底色（Zinc / Slate / Stone）搭配高对比的单点强调色（如祖母绿 Emerald、电光蓝 Electric Blue、焦橙 Burnt Orange）。
- **色彩一致性锁定**：选定强调色后，全页面统一贯彻。严禁页面上半部分用蓝色 CTA，底部突然变成粉色或青色。
- **禁用刻板的“暖纸+黄铜色”默认组合**：不要一遇到品质生活或消费品就无脑选用 `#f5f1ea` (米黄) + `#b08947` (黄铜)。可轮换选用：冷冽金属灰 (Cold Luxury)、深林墨绿 (Forest)、纯黑白配单点亮色 (Pure Monochrome + Pop)。

### 3.3 布局与节奏多元化 (Layout & Rhythm)
- **反居中偏见**：当 `DESIGN_VARIANCE > 4` 时，Hero 首屏严禁千篇一律的居中文本+居中按钮。优先采用 **50/50 左右分栏**、**左侧内容/右侧动态资产**、或**非对称留白**。
- **Hero 首屏收敛**：
  - 标题桌面端最多 2 行；副标题最多 20 个英文单词（或 40 个中文字符），最多 3-4 行。
  - 顶部内边距限制：桌面端顶部 padding 不得超过 `pt-24`（≈6rem），确保主 CTA 在 13-14 寸笔记本视口中完全可见。
- **Eyebrow（上标小标签）克制**：
  - 严禁在每一个 Section 上方都放一个 `uppercase tracking-widest` 的小标签！
  - **硬性上限**：每 3 个 Section 最多出现 1 个 Eyebrow。全页 9 个区块最多 3 个。
- **Section 布局去重禁令**：
  - 同一个页面内，相同的布局范式最多出现 1 次。例如“左图右文”最多连续使用 2 次，第 3 个区块必须打破（改为全宽引用、Bento 网格、横向滚动或纵向大卡片）。
  - 一个包含 8 个区块的页面，至少包含 4 种不同的布局语言。
- **Bento 网格单元真实性**：
  - 网格单元数量严格与实际内容匹配（3 项内容用 1+2 分割，5 项用 2+3）。严禁为了凑满 6 宫格而留空或塞入无意义的占位卡片。
  - Bento 内部至少有 2-3 个单元具备真实的视觉差异（如真实图片、对比背景、微交互图表），严禁 6 张一模一样的白底文字卡片。

### 3.4 真实视觉资产优先 (Visual Asset Strategy)
- 页面必须拥有真正的视觉焦点。**严禁使用 div 边框拼接“假截图”、“假控制台”或“假仪表盘”**。
- **资产优先级**：
  1. **图像生成工具优先**：利用可用的 `generate_image` 或 MCP 工具生成真实的高清摄影、产品特写、质感纹理与氛围图。
  2. **高画质占位源**：使用 `https://picsum.photos/seed/{descriptive-seed}/{w}/{h}`（种子词必须与上下文相关）。
  3. **品牌 Logo 墙**：使用真实 SVG 图标（如 Simple Icons CDN `https://cdn.simpleicons.org/{slug}/ffffff`），严禁纯文本拼装假 Logo。
  4. **明确占位标识**：若无可用图源，保留带尺寸规格的注释并提示用户替换。

### 3.5 交互细节与无障碍 (A11y & States)
- **按钮对比度与文本折行**：
  - 桌面端主 CTA 按钮文本**必须单行呈现**，严禁折行；文案精炼（通常 2-4 个字）。
  - 按钮文本与背景严格满足 WCAG AA 对比度（正文至少 4.5:1）。
  - 按钮 `:active` 状态必须提供微小的物理下压反馈（如 `active:scale-[0.98]` 或 `active:translate-y-[1px]`）。
- **完整状态生命周期**：
  - 所有数据与表单组件必须提供：Loading 骨架屏（与实际布局尺寸一致，严禁简陋的旋转菊花）、Empty 空状态插画/引导、Error 内联明确提示。

---

## 4. 交付前严格预检清单 (Pre-Flight Check)

在宣布任何前端代码交付完成前，必须逐项自检并确保 100% 通过：

- [ ] **Design Read 声明**：是否已在开头明确输出意图研判与风格定位？
- [ ] **三大旋钮合规**：布局离散度、动效烈度与视觉密度是否与场景契合？
- [ ] **首屏视口适配**：Hero 标题是否 ≤2 行？主 CTA 在无滚动情况下是否清晰可见？是否使用 `min-h-[100dvh]`？
- [ ] **排版字体合规**：是否避开了默认 Inter/Fraunces 滥用？斜体是否有下行保护？
- [ ] **色彩与强调色锁定**：全站是否锁定单一强调色？是否消除了未经审视的紫色/蓝色光晕？
- [ ] **布局无重复**：连续左右交替图文是否 ≤2 次？全页面是否有 ≥4 种布局模式？
- [ ] **Eyebrow 频次达标**：全站上标数量是否不超过总区块数的 1/3？
- [ ] **无假截图 / Div 拼凑**：产品与视觉展示是否采用真实图像、SVG 图标或真实微型组件？
- [ ] **响应式单列收拢**：所有多列 Grid / Flex 是否在 `< 768px` (md) 显式声明了优雅单列降级？
- [ ] **动效安全与性能**：是否全部基于 `transform` 与 `opacity` 硬件加速？是否严禁了 `window.onscroll` 监听？
- [ ] **完整代码无占位**：是否绝对杜绝了 `// TODO`、`// ... rest of code` 等懒惰截断，交付了可直接运行的完整源码？

---

## 5. 模块化扩展指南索引 (References)

按需查阅以下深度参考手册，获取具体场景的代码骨架与详细规则：

* **[设计系统选型与技术规范](file:///C:/Users/DELL/.gemini/config/skills/taste-frontend/references/design-systems.md)**：官方设计系统映射矩阵与最佳架构实践。
* **[细分审美流派指南](file:///C:/Users/DELL/.gemini/config/skills/taste-frontend/references/aesthetic-archetypes.md)**：极简杂志风、工业粗野风、高定代理商与暗黑科技风规范。
* **[动效与高级布局骨架](file:///C:/Users/DELL/.gemini/config/skills/taste-frontend/references/layout-and-motion.md)**：GSAP 钉扎滚动、水平视差、Motion 物理弹簧与交错进场标准代码。
* **[既有项目重构与审计协议](file:///C:/Users/DELL/.gemini/config/skills/taste-frontend/references/redesign-audit.md)**：针对既有前端代码库的渐进式高收益低风险重构流程。
* **[图像先行与提取工作流](file:///C:/Users/DELL/.gemini/config/skills/taste-frontend/references/image-to-code.md)**：结合 AI 生图进行深度排版、间距分析与高保真代码还原。
* **[Anti-Slop 绝对禁忌黑名单](file:///C:/Users/DELL/.gemini/config/skills/taste-frontend/references/anti-patterns.md)**：常见 AI 前端糟糕指纹与排查对照表。
