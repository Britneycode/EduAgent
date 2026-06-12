"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  MessageSquareText,
  PenLine,
  Presentation,
  Radar,
  Repeat2,
  Rocket,
  Route,
  Trophy,
} from "lucide-react";
import { isAuthenticated } from "@/lib/auth";

const FEATURES = [
  { icon: BrainCircuit, title: "8 Agent 协同", desc: "Router、Planner、Tutor、Doc、Quiz、Code、Media、Reading 分工协作" },
  { icon: ClipboardList, title: "智能出题", desc: "选择题、判断题、简答题一键生成，逐题交互，答完即解析" },
  { icon: Presentation, title: "PPT 自动生成", desc: "AI 提炼知识要点，生成适合课堂展示的教学演示资源" },
  { icon: Radar, title: "学习画像", desc: "8 维度刻画学习状态，动态更新认知风格、薄弱点和兴趣方向" },
  { icon: Repeat2, title: "错题复习", desc: "按间隔复习节奏自动排期，错题回归提醒，知识盲点逐个击破" },
  { icon: BookOpen, title: "知识中枢", desc: "课程文档向量化存储，RAG 混合检索，DAG 知识图谱可视化" },
  { icon: Route, title: "学习路径", desc: "基于前置知识的个性化路径，自动推荐下一步学习方向" },
  { icon: BarChart3, title: "学习报告", desc: "学习统计、趋势图表、知识点掌握度一览，数据驱动进步" },
];

export default function HomePage() {
  const router = useRouter();
  const [shouldRedirect, setShouldRedirect] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setShouldRedirect(isAuthenticated());
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (shouldRedirect) {
      router.replace("/chat");
    }
  }, [router, shouldRedirect]);

  if (shouldRedirect) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-parchment)]">
        <div className="text-center">
          <h1 className="mb-4 text-3xl font-serif text-[var(--color-terracotta)]">EduAgent</h1>
          <p className="text-[var(--color-warm-gray-500)]">正在准备学习环境...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-parchment)]">
      {/* 导航 */}
      <header className="border-b border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)]/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-2xl font-medium text-[var(--color-terracotta)] font-serif">EduAgent</span>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-[var(--color-warm-gray-600)] hover:text-[var(--color-terracotta)]">登录</Link>
            <Link href="/register" className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-terracotta)] px-5 py-2 text-sm text-white hover:bg-[var(--color-terracotta-hover)]">
              免费注册
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden px-6 py-20 md:py-32">
        <div className="mx-auto max-w-4xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-[var(--color-ivory)] px-4 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)]">
            <Trophy className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
            基于 LangGraph 多智能体架构 · 讯飞星火驱动
          </div>
          <h1 className="mb-6 text-5xl font-medium leading-tight text-[var(--color-warm-gray-800)] font-serif md:text-7xl">
            你的 <span className="text-[var(--color-terracotta)]">AI</span> 个性化<br />学习伙伴
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-[var(--color-warm-gray-500)]">
            EduAgent 不是简单的问答机器人——它由 8 个协同 AI Agent 驱动，
            深度理解你的学习画像，为你量身生成讲义、题目、代码、PPT、思维导图和动画讲解。
          </p>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-2xl bg-[var(--color-terracotta)] px-10 py-4 text-lg font-medium text-white shadow-[var(--shadow-whisper)] transition-all hover:bg-[var(--color-terracotta-hover)]"
            >
              免费开始使用
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/login"
              className="rounded-2xl bg-[var(--color-ivory)] px-10 py-4 text-lg text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] transition-all hover:ring-[var(--color-terracotta)]"
            >
              已有账号？登录
            </Link>
          </div>
        </div>
      </section>

      {/* 功能卡片 */}
      <section className="px-6 pb-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <h2 className="mb-3 text-3xl font-serif text-[var(--color-warm-gray-800)] md:text-4xl">核心能力一览</h2>
            <p className="text-[var(--color-warm-gray-500)]">一切围绕「个性化学习」设计</p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-2xl bg-[var(--color-ivory)] p-6 ring-1 ring-[var(--color-warm-gray-200)] transition-all hover:shadow-[var(--shadow-ring-warm)]">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-parchment)] text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
                  <f.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-3 mb-1 font-serif text-lg text-[var(--color-warm-gray-800)]">{f.title}</h3>
                <p className="text-sm leading-6 text-[var(--color-warm-gray-500)]">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)] px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-12 text-3xl font-serif text-[var(--color-warm-gray-800)] md:text-4xl">三步开始学习</h2>
          <div className="grid gap-8 md:grid-cols-3">
            {[
              { step: "1", icon: PenLine, title: "完善画像", desc: "花 2 分钟告诉 AI 你的专业、目标和学习偏好" },
              { step: "2", icon: MessageSquareText, title: "说出需求", desc: "自然语言描述：梳理机器学习路径，或出几道题练练手" },
              { step: "3", icon: Rocket, title: "开始学习", desc: "AI 为你生成个性化学习资料，练习、复习、追踪全面提升" },
            ].map((s) => (
              <div key={s.step} className="rounded-2xl bg-[var(--color-parchment)] p-6 ring-1 ring-[var(--color-warm-gray-200)]">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-terracotta)]/10 text-[var(--color-terracotta)]">
                  <s.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 font-serif text-lg text-[var(--color-warm-gray-800)]">{s.title}</h3>
                <p className="text-sm text-[var(--color-warm-gray-500)]">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20 text-center">
        <div className="mx-auto max-w-2xl">
          <h2 className="mb-4 text-3xl font-serif text-[var(--color-warm-gray-800)] md:text-4xl">准备好升级你的学习方式了吗？</h2>
          <p className="mb-8 text-[var(--color-warm-gray-500)]">免费注册，即刻体验 AI 驱动的个性化学习</p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-2xl bg-[var(--color-terracotta)] px-12 py-4 text-lg font-medium text-white shadow-[var(--shadow-whisper)] transition-all hover:bg-[var(--color-terracotta-hover)]"
          >
            免费注册
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)] px-6 py-8 text-center">
        <p className="text-xs text-[var(--color-warm-gray-400)]">
          © 2025 EduAgent · 基于 LangGraph + 讯飞星火 · 高等教育 AI 学习平台
        </p>
      </footer>
    </div>
  );
}
