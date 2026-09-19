# 细分审美流派指南 (Aesthetic Archetypes)

当需求研判指向特定的审美分支时，查阅本指南执行精准的视觉与组件架构落地。每个项目**仅选择一种主导流派并贯彻到底**，严禁在同一页面内杂糅冲突的视觉语言。

---

## 流派一：极简杂志风 (Premium Editorial Minimalism)

> **适用场景**：高端工作室、设计总监作品集、建筑与艺术机构、思想领袖个人主页、深度内容刊物。

### 1. 核心视觉特征
- **色彩底色**：纯白 `#FFFFFF` 或温润纸感 `#F7F6F3` / `#FBFBFA`。
- **文字色彩**：严禁纯黑 `#000000`，使用碳墨深灰 `#111111` 或 `#2F3437`；次要信息使用低饱和灰 `#787774`。
- **点缀色 (Spot Pastels)**：极其克制的水洗粉彩，仅用于小标签或单点图标背景：
  - 淡青蓝：`#E1F3FE` (文本 `#1F6C9F`)
  - 嫩芽绿：`#EDF3EC` (文本 `#346538`)
  - 暖草黄：`#FBF3DB` (文本 `#956400`)
- **排版结构**：
  - 标题：高对比度衬线体 (`PP Editorial New`, `Playfair Display`, `Newsreader`)，配合极紧密字距 `letter-spacing: -0.03em` 与行高 `leading-[1.1]`。
  - 正文：极简几何无衬线 (`SF Pro`, `Geist`, `Switzer`)，行高 `leading-[1.6]`，单行上限 65 字符。
  - 数据与元数据：等宽字体 (`Geist Mono`, `JetBrains Mono`)。

### 2. 组件与网格实现
- **无阴影卡片 (Flat Bento)**：边框严格使用 `1px solid #EAEAEA` 或 `rgba(0,0,0,0.06)`，圆角小而克制 (`rounded-lg` 8px 或 `rounded-xl` 12px)，完全弃用 Tailwind 的重阴影。
- **极简折叠面板 (FAQ)**：剥离多余的外包容器，仅通过 `border-b border-[#EAEAEA]` 分割，右侧使用极细的 `+` 与 `-` 符号切换。
- **实体快捷键 (`<kbd>`)**：`border: 1px solid #EAEAEA; background: #F7F6F3; font-family: monospace; border-radius: 4px;`。

---

## 流派二：工业粗野与战术遥测 (Industrial Brutalism & Telemetry)

> **适用场景**：硬核开发者工具、军工级安全系统、硬件产品、数据密集的控制台、赛博朋克先锋项目。

### 1. 核心视觉特征
- **范式二选一**：
  - **瑞士工业印刷 (浅色模式)**：无漂白文档纸底色 `#F4F4F0` + 碳墨字 `#050505` + 警示航空红 `#FF2A2A`（唯一的强调色）。
  - **战术终端 CRT (深色模式)**：断电晶体管黑 `#0A0A0A` + 荧光白字 `#EAEAEA` + 航空红 `#FF2A2A`（可选单点终端绿 `#4AF626` 仅用于单个运行状态指示灯）。
- **几何与轮廓**：**绝对纯直角 (`rounded-none` / 0px)**，彻底禁用圆角与柔和渐变。
- **结构分割线**：利用 `1px` 或 `2px solid` 实线清晰划定功能区块，使用 `<hr>` 贯穿全宽。

### 2. 标志性排版与符号
- **巨型大写标题**：大写无衬线粗体 (`Neue Haas Grotesk`, `Inter Black`, `Archivo Black`)，`tracking-[-0.05em]`，行高 `0.9`，采用 `clamp(3.5rem, 8vw, 12rem)` 极限缩放。
- **结构化元数据**：全大写等宽字体 (`JetBrains Mono`, `IBM Plex Mono`)，字距宽松 `tracking-wider`。
- **工程装饰符号**：
  - 括号定界：`[ SYSTEM_READY ]`、`< TELEMETRY // 01 >`
  - 物理十字准星：在网格交汇处放置 `+` 或 `x`
  - 工业标志：将 `®`, `©`, `™` 作为几何版面平衡符号
  - 拟真 CRT 扫描线：`background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px);`

---

## 流派三：高定代理商级视觉与触感深度 ($150k Agency High-End)

> **适用场景**：顶级消费级品牌、奢品科技、现代先锋 SaaS、苹果质感营销页。

### 1. 双层机械倒角架构 (Double-Bezel / Doppelrand)
避免将卡片或容器扁平地贴在背景上，模拟精密加工的硬件质感（如阳极氧化铝托盘中的悬浮玻璃）：
```tsx
// 双层倒角容器标准结构
<div className="p-1.5 md:p-2 rounded-[2rem] bg-black/5 dark:bg-white/5 ring-1 ring-black/5 dark:ring-white/10">
  <div className="p-8 rounded-[calc(2rem-0.5rem)] bg-white dark:bg-zinc-900 shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)] shadow-xl">
    {children}
  </div>
</div>
```

### 2. 嵌套岛屿 CTA 按钮 (Button-in-Button)
主行动按钮采用完全圆润的胶囊形态 (`rounded-full`)，尾部箭头图标不裸露摆放，而是嵌套在独立的圆形子容器中：
```tsx
<button className="group relative inline-flex items-center gap-4 pl-6 pr-2 py-2 rounded-full bg-zinc-950 text-white font-medium hover:bg-zinc-800 transition-all duration-300 active:scale-[0.98]">
  <span>探索全部作品</span>
  <span className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:scale-105">
    <ArrowUpRight className="w-4 h-4" />
  </span>
</button>
```

### 3. 悬浮流体导航岛 (Fluid Island Nav)
- 顶部导航脱离屏幕上边缘，作为居中悬浮药丸呈现 (`mt-6 mx-auto w-max max-w-5xl rounded-full backdrop-blur-xl bg-white/70 dark:bg-zinc-950/70 border border-white/20 dark:border-zinc-800/80 shadow-lg px-6 py-3`)。
- 移动端汉堡菜单展开时，采用全屏高斯模糊遮罩 (`backdrop-blur-3xl bg-black/80`)，菜单项采用自上而下的遮罩渐入交错动画。

---

## 流派四：暗黑极客与现代化开发者工具 (Modern Dark Tech)

> **适用场景**：AI 基础设施、代码编辑器、云计算管理平台、CLI 工具推广页。

### 1. 核心视觉特征
- **底色规范**：`#09090B` (Zinc-950) 或 `#050505`，杜绝生硬的纯黑 `#000000`。
- **微结构线**：极细半透明白色边框 (`border-white/10` 或 `border-zinc-800`)。
- **单色激光强调**：使用冷色调单点高对比强调色（如亮青 `#06B6D4`、翡翠绿 `#10B981` 或电光蓝 `#3B82F6`）。
- **真实终端视口**：上方带 macOS 风格三色圆点（微缩灰度），内部展示真实的 CLI 命令、语法高亮代码或 JSON 响应，严禁胡乱拼凑无意义的假数据。
