# 动效与高级布局标准骨架 (Layout & Motion Skeletons)

动效必须服务于信息层级与交互反馈，**严禁无理由的滥用**。若设定了 `MOTION_INTENSITY > 4`，页面必须呈现出严谨、丝滑且符合物理规律的真实动效，而非半途而废的半成品。

---

## 1. GSAP 钉扎层叠卡片标准骨架 (Sticky Stack)

当页面需要实现多张大卡片在向下滚动过程中逐层固定并产生缩放/虚化退场时，必须使用以下经过工业级验证的标准 GSAP + ScrollTrigger 架构：

```tsx
"use client";

import React, { useRef, useEffect } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

interface StickyStackProps {
  cards: React.ReactNode[];
}

export function StickyStack({ cards }: StickyStackProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 检测用户是否开启系统级“减少动态效果”
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || !containerRef.current) return;

    const ctx = gsap.context(() => {
      const cardElements = gsap.utils.toArray<HTMLElement>(".sticky-stack-card");

      cardElements.forEach((card, index) => {
        // 最后一组卡片无需被后置卡片覆盖
        if (index === cardElements.length - 1) return;

        // 1. 钉扎当前卡片到视口顶部
        ScrollTrigger.create({
          trigger: card,
          start: "top top",
          endTrigger: cardElements[cardElements.length - 1],
          end: "top top",
          pin: true,
          pinSpacing: false,
        });

        // 2. 当下一张卡片从视口底部进入并推向顶部时，当前卡片产生微缩放与淡出
        gsap.to(card, {
          scale: 0.92,
          opacity: 0.5,
          ease: "none",
          scrollTrigger: {
            trigger: cardElements[index + 1],
            start: "top bottom",
            end: "top top",
            scrub: true,
          },
        });
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="sticky-stack-card sticky top-0 min-h-[100dvh] flex items-center justify-center p-4 md:p-8"
        >
          {card}
        </div>
      ))}
    </div>
  );
}
```

---

## 2. GSAP 水平滚动劫持标准骨架 (Horizontal Pan)

将纵向滚轮驱动转化为横向内容滑动的标准实现方案：

```tsx
"use client";

import React, { useRef, useEffect } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function HorizontalPan({ children }: { children: React.ReactNode }) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || !wrapperRef.current || !trackRef.current) return;

    const ctx = gsap.context(() => {
      const totalScrollWidth = trackRef.current!.scrollWidth;
      const viewportWidth = window.innerWidth;
      const distance = totalScrollWidth - viewportWidth;

      gsap.to(trackRef.current, {
        x: -distance,
        ease: "none",
        scrollTrigger: {
          trigger: wrapperRef.current,
          start: "top top",
          end: () => `+=${distance}`,
          pin: true,
          scrub: 1,
          invalidateOnRefresh: true,
        },
      });
    }, wrapperRef);

    return () => ctx.revert();
  }, []);

  return (
    <section ref={wrapperRef} className="relative w-full overflow-hidden bg-zinc-950 text-white">
      <div ref={trackRef} className="flex h-[100dvh] items-center gap-8 px-12 md:px-24">
        {children}
      </div>
    </section>
  );
}
```

---

## 3. Motion (`motion/react`) 优雅交错渐入骨架 (Reveal Stagger)

对于无需复杂钉扎的列表、特性网格、客户评价，优先使用轻量的 `motion/react` 视口触发：

```tsx
"use client";

import React from "react";
import { motion, useReducedMotion } from "motion/react";

interface RevealGridProps {
  items: Array<{ title: string; desc: string; icon?: React.ReactNode }>;
}

export function RevealGrid({ items }: RevealGridProps) {
  const shouldReduceMotion = useReducedMotion();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        ease: [0.16, 1, 0.3, 1], // 自定义弹性缓动
      },
    },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      className="grid grid-cols-1 md:grid-cols-3 gap-6"
    >
      {items.map((item, i) => (
        <motion.div
          key={i}
          variants={itemVariants}
          className="p-8 rounded-2xl bg-zinc-900/50 border border-zinc-800 backdrop-blur-sm hover:border-zinc-700 transition-colors"
        >
          {item.icon && <div className="mb-4 text-emerald-400">{item.icon}</div>}
          <h3 className="text-xl font-semibold text-white mb-2">{item.title}</h3>
          <p className="text-zinc-400 text-sm leading-relaxed">{item.desc}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}
```

---

## 4. 磁吸物理与微交互 (Magnetic Physics)

为按钮或可交互卡片添加磁吸效果时，**严禁使用 React State**，必须使用 `useMotionValue` 和 `useSpring`：

```tsx
"use client";

import React, { useRef } from "react";
import { motion, useMotionValue, useSpring } from "motion/react";

export function MagneticButton({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  const x = useMotionValue(0);
  const y = useMotionValue(0);

  // 物理弹簧参数：刚度 150，阻尼 15
  const springX = useSpring(x, { stiffness: 150, damping: 15, mass: 0.1 });
  const springY = useSpring(y, { stiffness: 150, damping: 15, mass: 0.1 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const { clientX, clientY } = e;
    const { left, top, width, height } = ref.current.getBoundingClientRect();
    const centerX = left + width / 2;
    const centerY = top + height / 2;
    x.set((clientX - centerX) * 0.3);
    y.set((clientY - centerY) * 0.3);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      ref={ref}
      style={{ x: springX, y: springY }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="inline-block cursor-pointer"
    >
      {children}
    </motion.div>
  );
}
```

---

## 5. 动效严令禁止的反模式 (Forbidden Animation Patterns)

1. **严禁 `window.addEventListener("scroll", ...)`**：每帧触发且不受调度控制，极易引发严重掉帧卡顿。必须使用 `useScroll()`、`IntersectionObserver` 或 GSAP `ScrollTrigger`。
2. **严禁在滚动回调中更新 React State**：滚动时 `setState` 会导致整棵组件树每秒重渲染 60-120 次，移动端直接卡死崩溃。
3. **严禁对 `top`, `left`, `width`, `height`, `margin` 进行动画**：这会触发浏览器的重排 (Layout/Reflow) 与重绘 (Repaint)。**只能**对 `transform` (translate/scale/rotate) 与 `opacity` 进行硬件加速过渡。
4. **跑马灯 (Marquee) 限制**：一个页面最多只允许出现 **1 次** 水平跑马灯（通常用于 Logo 墙或合作伙伴）。多次堆砌跑马灯属于典型的偷懒排版。
