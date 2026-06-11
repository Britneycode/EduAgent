"use client";

import { useEffect, useState } from "react";
import { fetchReviewQueue, updateReviewItem } from "@/lib/api";
import type { ReviewItem } from "@/lib/types";

const QUESTION_TYPE_LABELS: Record<string, string> = {
  choice: "选择题",
  judge: "判断题",
  short_answer: "简答题",
};

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [revealedIds, setRevealedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  useEffect(() => {
    fetchReviewQueue()
      .then((queue) => {
        setItems(queue);
        setLoadError(null);
      })
      .catch((err) => {
        setItems([]);
        setLoadError(err instanceof Error ? err.message : "获取复习队列失败");
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleUpdate(itemId: number, mastered: boolean) {
    if (updatingId) return;
    setUpdatingId(itemId);
    setActionError(null);
    try {
      await updateReviewItem(itemId, mastered);
      setItems((current) => current.filter((item) => item.id !== itemId));
      setRevealedIds((current) => {
        const next = new Set(current);
        next.delete(itemId);
        return next;
      });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "更新复习状态失败");
    } finally {
      setUpdatingId(null);
    }
  }

  function toggleReveal(itemId: number) {
    setRevealedIds((current) => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-serif text-2xl text-[var(--color-warm-gray-800)]">
              今日复习
            </h1>
            <p className="mt-1 text-sm text-[var(--color-warm-gray-500)]">
              错题本 · 按艾宾浩斯间隔复习，把到期错题快速过一遍
            </p>
          </div>
          {!loading && !loadError && items.length > 0 && (
            <div className="flex flex-wrap items-center gap-3">
              <StatBadge label="待复习" value={String(items.length)} color="bg-red-50 text-red-700" />
              <StatBadge label="已复习总次数" value={String(items.reduce((s, i) => s + i.review_count, 0))} color="bg-blue-50 text-blue-700" />
              <StatBadge
                label="涉及知识点"
                value={String(new Set(items.map((i) => i.knowledge_point).filter(Boolean)).size)}
                color="bg-green-50 text-green-700"
              />
            </div>
          )}
        </div>

        {loading ? (
          <div className="rounded-xl bg-[var(--color-ivory)] p-8 text-center text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
            正在整理今日复习...
          </div>
        ) : loadError ? (
          <div className="rounded-xl bg-red-50 p-5 text-sm text-red-700 ring-1 ring-red-100">
            {loadError}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl bg-[var(--color-ivory)] px-6 py-14 text-center ring-1 ring-[var(--color-warm-gray-200)]">
            <h2 className="font-serif text-xl text-[var(--color-warm-gray-800)]">
              今天没有到期复习
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--color-warm-gray-500)]">
              暂时没有需要回看的错题。完成新的练习后，需要巩固的知识点会自动出现在这里。
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {actionError && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-100">
                {actionError}
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-2">
              {items.map((item) => {
                const revealed = revealedIds.has(item.id);
                const updating = updatingId === item.id;

                return (
                  <article
                    key={item.id}
                    className="rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]"
                  >
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[var(--color-warm-gray-800)] px-2.5 py-1 text-[11px] text-white">
                        {QUESTION_TYPE_LABELS[item.question_type] ?? item.question_type}
                      </span>
                      <span className="rounded-full bg-[var(--color-terracotta)]/10 px-2.5 py-1 text-[11px] text-[var(--color-terracotta)]">
                        {item.knowledge_point || "未标注知识点"}
                      </span>
                      <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                        已复习 {item.review_count} 次
                      </span>
                    </div>

                    <p className="text-sm leading-6 text-[var(--color-warm-gray-800)]">
                      {item.question_text}
                    </p>

                    <div className="mt-3 rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-xs leading-5 text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)]">
                      <span className="font-medium text-[var(--color-warm-gray-700)]">
                        上次作答：
                      </span>
                      {item.user_answer || "未作答"}
                    </div>

                    <div className="mt-3">
                      <button
                        type="button"
                        onClick={() => toggleReveal(item.id)}
                        className="rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]"
                      >
                        {revealed ? "收起答案" : "查看答案与解析"}
                      </button>
                    </div>

                    {revealed && (
                      <div className="mt-3 space-y-2 rounded-lg bg-[var(--color-parchment)] p-3 ring-1 ring-[var(--color-warm-gray-200)]">
                        <div className="text-xs leading-5 text-[var(--color-warm-gray-700)]">
                          <span className="font-medium text-[var(--color-warm-gray-800)]">
                            正确答案：
                          </span>
                          {item.correct_answer}
                        </div>
                        {item.explanation && (
                          <p className="text-xs leading-5 text-[var(--color-warm-gray-600)]">
                            {item.explanation}
                          </p>
                        )}
                      </div>
                    )}

                    <div className="mt-4 flex flex-wrap justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => void handleUpdate(item.id, false)}
                        disabled={updating}
                        className="rounded-lg px-3 py-2 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {updating ? "更新中..." : "还不熟"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleUpdate(item.id, true)}
                        disabled={updating}
                        className="rounded-lg bg-[var(--color-terracotta)] px-3 py-2 text-xs text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        已掌握
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatBadge({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className={`rounded-full px-3 py-1.5 text-xs ${color} ring-1 ring-black/5`}>
      <span className="font-medium">{value}</span>
      <span className="ml-1 opacity-60">{label}</span>
    </div>
  );
}
