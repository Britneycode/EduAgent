"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Clock3,
  FileQuestion,
  Flame,
  Lightbulb,
  Map,
  Presentation,
  Repeat2,
  Send,
} from "lucide-react";
import { createSession, fetchLearningDashboard, fetchReviewQueue, fetchProfile } from "@/lib/api";
import { setPendingMessage } from "@/lib/pendingMessage";
import { VoiceInput } from "@/components/chat/VoiceInput";
import type { LearningDashboard, ReviewItem, Profile } from "@/lib/types";

const STARTER_PROMPTS = [
  { label: "梳理学习路径", text: "帮我梳理《人工智能导论》的学习路径", icon: Map },
  { label: "出练习题", text: "给我出一组神经网络入门练习题", icon: FileQuestion },
  { label: "生成 PPT", text: "帮我做一个 Python 基础的 PPT", icon: Presentation },
  { label: "答疑解惑", text: "什么是梯度下降？为什么它很重要？", icon: Lightbulb },
];

function formatMinutes(sec: number): string {
  const m = Math.floor(sec / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}小时${m % 60}分`;
  return `${m}分钟`;
}

export default function ChatHomePage() {
  const router = useRouter();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [dashboard, setDashboard] = useState<LearningDashboard | null>(null);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchLearningDashboard().catch(() => null),
      fetchReviewQueue(4).catch(() => []),
      fetchProfile().catch(() => null),
    ]).then(([d, r, p]) => {
      setDashboard(d);
      setReviews(r);
      setProfile(p);
      setLoading(false);
    });
  }, []);

  // 学习打卡
  const [streak, setStreak] = useState(0);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const today = new Date().toISOString().slice(0, 10);
      const stored = JSON.parse(localStorage.getItem("eduagent_checkin") || "{}");
      const lastDate = stored.lastDate || "";
      if (lastDate !== today) {
        const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
        const newStreak = lastDate === yesterday ? (stored.streak || 0) + 1 : 1;
        localStorage.setItem("eduagent_checkin", JSON.stringify({ lastDate: today, streak: newStreak }));
        setStreak(newStreak);
      } else {
        setStreak(stored.streak || 1);
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  const handleSend = async (message?: string) => {
    const text = (message ?? input).trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const sessionId = await createSession();
      setPendingMessage(text);
      router.push(`/chat/${sessionId}`);
    } catch {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasStats = dashboard && dashboard.summary.total_activities > 0;

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-6 md:py-10">
        {/* 欢迎区 */}
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-4xl font-medium text-[var(--color-warm-gray-800)] font-serif md:text-5xl">
            EduAgent
          </h1>
          <p className="text-base text-[var(--color-warm-gray-500)]">
            个性化 AI 学习助手 · 随时答疑、出题、生成资料
          </p>
          {streak > 0 && (
            <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-[var(--color-ivory)] px-3 py-1 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)]">
              <Flame className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
              连续学习 <span className="font-medium text-[var(--color-terracotta)]">{streak}</span> 天
            </div>
          )}
        </div>

        {/* 主输入框 */}
        <div className="mb-8 rounded-2xl bg-[var(--color-ivory)] p-4 shadow-sm ring-1 ring-[var(--color-warm-gray-200)]">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="描述你的学习需求，开始一段新对话..."
            rows={2}
            className="w-full resize-none rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm leading-6 ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            disabled={sending}
          />
          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-[var(--color-warm-gray-400)]">
              按 Enter 发送 · 试试输入「出几道题」或「帮我做个 PPT」
            </p>
            <div className="flex items-center gap-2">
              <VoiceInput onResult={(text) => setInput((prev) => prev + text)} disabled={sending} />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || sending}
                className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-terracotta)] px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sending ? "创建中..." : "开始对话"}
              {!sending && <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* 快捷操作 */}
        <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STARTER_PROMPTS.map((p) => (
            <button
              key={p.label}
              type="button"
              disabled={sending}
              onClick={() => handleSend(p.text)}
              className="flex items-center gap-3 rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-left ring-1 ring-[var(--color-warm-gray-200)] transition-all hover:bg-[var(--color-parchment)] hover:ring-[var(--color-terracotta)]/40 disabled:opacity-50"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-parchment)] text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
                <p.icon className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-medium text-[var(--color-warm-gray-700)]">{p.label}</p>
                <p className="text-[11px] text-[var(--color-warm-gray-400)] truncate max-w-[140px]">{p.text}</p>
              </div>
            </button>
          ))}
        </div>

        {/* 数据面板 */}
        {!loading && hasStats && (
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={BookOpen}
              label="学习活动"
              value={String(dashboard!.summary.total_activities)}
              href="/analytics"
            />
            <StatCard
              icon={Clock3}
              label="学习时长"
              value={formatMinutes(dashboard!.summary.total_duration_sec)}
              href="/analytics"
            />
            <StatCard
              icon={FileQuestion}
              label="测验均分"
              value={`${Math.round(dashboard!.summary.average_quiz_score)}分`}
              href="/analytics"
            />
            <StatCard
              icon={Repeat2}
              label="待复习"
              value={`${dashboard!.summary.pending_review_count}项`}
              href="/review"
              highlight={dashboard!.summary.pending_review_count > 0}
            />
          </div>
        )}

        {/* 两栏：画像概览 + 待复习 */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* 画像卡片 */}
          <div className="rounded-2xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-serif text-lg text-[var(--color-warm-gray-800)]">我的学习画像</h3>
              <Link href="/profile" className="inline-flex items-center gap-1 text-xs text-[var(--color-terracotta)] hover:underline">
                完善画像
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {profile?.major ? (
              <div className="space-y-2 text-sm">
                <ProfileRow label="专业" value={profile.major} />
                <ProfileRow label="年级" value={profile.grade} />
                <ProfileRow label="学习目标" value={profile.learning_goal} />
                <ProfileRow label="认知风格" value={profile.cognitive_style} />
                {profile.weak_points.length > 0 && (
                  <div className="flex gap-2 pt-1">
                    <span className="text-xs text-[var(--color-warm-gray-500)]">薄弱点：</span>
                    <span className="text-xs text-red-600">{profile.weak_points.slice(0, 3).join("、")}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-6 text-center">
                <p className="mb-3 text-sm text-[var(--color-warm-gray-500)]">
                  还没有学习画像，完善后可获得更精准的学习推荐
                </p>
                <Link
                  href="/profile"
                  className="inline-block rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-xs text-white hover:bg-[var(--color-terracotta-hover)]"
                >
                  去完善画像
                </Link>
              </div>
            )}
          </div>

          {/* 今日复习 */}
          <div className="rounded-2xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-serif text-lg text-[var(--color-warm-gray-800)]">
                今日复习 {reviews.length > 0 && <span className="text-sm text-red-500">({reviews.length})</span>}
              </h3>
              <Link href="/review" className="inline-flex items-center gap-1 text-xs text-[var(--color-terracotta)] hover:underline">
                查看全部
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {reviews.length === 0 ? (
              <div className="py-6 text-center">
                <p className="inline-flex items-center gap-2 text-sm text-[var(--color-warm-gray-500)]">
                  <CheckCircle2 className="h-4 w-4 text-[var(--color-resource-mindmap)]" />
                  今天没有到期复习，继续保持！
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {reviews.slice(0, 3).map((r) => (
                  <Link
                    key={r.id}
                    href="/review"
                    className="block rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] hover:ring-[var(--color-terracotta)]/40"
                  >
                    <span className="line-clamp-1">{r.question_text}</span>
                    <span className="mt-1 block text-[11px] text-[var(--color-warm-gray-400)]">
                      {r.knowledge_point} · 已复习{r.review_count}次
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 知识掌握概览 */}
        {dashboard && dashboard.knowledge_mastery.length > 0 && (
          <div className="mt-6 rounded-2xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
            <h3 className="mb-4 font-serif text-lg text-[var(--color-warm-gray-800)]">知识点掌握</h3>
            <div className="flex flex-wrap gap-2">
              {dashboard.knowledge_mastery.slice(0, 10).map((k) => {
                const colors: Record<string, string> = {
                  mastered: "bg-green-50 text-green-700 ring-green-200",
                  in_progress: "bg-blue-50 text-blue-700 ring-blue-200",
                  weak: "bg-red-50 text-red-700 ring-red-200",
                  unknown: "bg-gray-50 text-gray-500 ring-gray-200",
                };
                return (
                  <span
                    key={k.knowledge_point}
                    className={`rounded-full px-3 py-1 text-xs ring-1 ${colors[k.level] || colors.unknown}`}
                  >
                    {k.knowledge_point}
                    <span className="ml-1 opacity-60">{k.average_score}分</span>
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
    </div>
  );
}

function StatCard({
  icon, label, value, href, highlight,
}: {
  icon: typeof BarChart3; label: string; value: string; href: string; highlight?: boolean;
}) {
  const Icon = icon;
  return (
    <Link
      href={href}
      className={`rounded-xl bg-[var(--color-ivory)] p-4 ring-1 transition-all hover:ring-[var(--color-terracotta)]/40 ${
        highlight ? "ring-[var(--color-terracotta)]" : "ring-[var(--color-warm-gray-200)]"
      }`}
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-parchment)] text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
        <Icon className="h-5 w-5" />
      </span>
      <p className="mt-2 text-lg font-medium text-[var(--color-warm-gray-800)]">{value}</p>
      <p className="text-xs text-[var(--color-warm-gray-500)]">{label}</p>
    </Link>
  );
}

function ProfileRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <span className="shrink-0 text-xs text-[var(--color-warm-gray-400)] w-14">{label}</span>
      <span className="text-xs text-[var(--color-warm-gray-700)]">{value}</span>
    </div>
  );
}
