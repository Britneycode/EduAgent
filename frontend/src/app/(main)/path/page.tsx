"use client";

import { useEffect, useState, useCallback } from "react";
import {
  createLearningPath,
  fetchLearningPaths,
  fetchLearningPath,
  updateNodeStatus,
  fetchPathRecommendations,
  fetchWikiCourses,
  fetchWikiChapters,
  fetchWikiTree,
} from "@/lib/api";
import { LearningPathGraph } from "@/components/learning/LearningPathGraph";
import type {
  LearningPath,
  LearningPathSummary,
  LearningPathNode,
  PathRecommendation,
  WikiCourse,
} from "@/lib/types";

export default function PathPage() {
  const [courses, setCourses] = useState<WikiCourse[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);
  const [paths, setPaths] = useState<LearningPathSummary[]>([]);
  const [activePath, setActivePath] = useState<LearningPath | null>(null);
  const [recommendation, setRecommendation] = useState<PathRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [goal, setGoal] = useState("");
  const [generating, setGenerating] = useState(false);
  const [conceptSuggestions, setConceptSuggestions] = useState<string[]>([]);

  useEffect(() => {
    fetchLearningPaths()
      .then(setPaths)
      .catch(() => setPaths([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchWikiCourses()
      .then((items) => {
        setCourses(items);
        const defaultCourse = items.find((item) => item.is_default) || items[0];
        setSelectedCourseId(defaultCourse?.id ?? null);
      })
      .catch(() => {
        setCourses([]);
        setSelectedCourseId(null);
      });
  }, []);

  useEffect(() => {
    if (!selectedCourseId) {
      setConceptSuggestions([]);
      return;
    }
    fetchWikiChapters(selectedCourseId)
      .then(async (chapters) => {
        const names: string[] = [];
        for (const ch of chapters) {
          try {
            const data = await fetchWikiTree(ch.id, selectedCourseId);
            for (const c of data.concepts || []) {
              names.push(c.name);
            }
          } catch { /* skip */ }
        }
        setConceptSuggestions(names);
      })
      .catch(() => {});
  }, [selectedCourseId]);

  const loadPath = useCallback(async (pathId: number) => {
    try {
      const [path, rec] = await Promise.all([
        fetchLearningPath(pathId),
        fetchPathRecommendations(pathId),
      ]);
      setActivePath(path);
      setRecommendation(rec);
    } catch {
      setActivePath(null);
      setRecommendation(null);
    }
  }, []);

  const handleCreate = async () => {
    if (!goal.trim() || generating) return;
    setGenerating(true);
    try {
      const path = await createLearningPath(
        goal.trim(),
        undefined,
        selectedCourseId
      );
      setPaths((prev) => [
        {
          id: path.id,
          title: path.title,
          goal_topic: path.goal_topic,
          status: path.status,
          node_count: path.nodes.length,
          progress: path.progress,
          created_at: path.created_at,
          updated_at: path.updated_at,
        },
        ...prev,
      ]);
      setGoal("");
      await loadPath(path.id);
    } catch {
      // 创建失败不处理
    } finally {
      setGenerating(false);
    }
  };

  const toggleNodeStatus = async (node: LearningPathNode) => {
    if (!activePath) return;
    const newStatus = node.status === "completed" ? "pending" : "completed";
    try {
      const updated = await updateNodeStatus(activePath.id, node.concept, newStatus);
      setActivePath(updated);
      const rec = await fetchPathRecommendations(updated.id);
      setRecommendation(rec);
      setPaths((prev) =>
        prev.map((p) =>
          p.id === updated.id ? { ...p, progress: updated.progress } : p
        )
      );
    } catch {
      // 更新失败不处理
    }
  };

  const progress = activePath
    ? Math.round(activePath.progress * 100)
    : 0;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 font-serif text-2xl text-[var(--color-warm-gray-800)]">
        学习路径
      </h1>

      {/* 创建路径 */}
      <div className="mb-8 rounded-xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
        <div className="mb-3 grid gap-3 md:grid-cols-[240px_1fr]">
          <label>
            <span className="mb-1 block text-xs text-[var(--color-warm-gray-500)]">
              课程
            </span>
            <select
              value={selectedCourseId || ""}
              onChange={(event) => setSelectedCourseId(event.target.value || null)}
              className="w-full rounded-xl bg-[var(--color-parchment)] px-3 py-2.5 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            >
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
          </label>
          <p className="self-end text-sm text-[var(--color-warm-gray-600)]">
            输入目标知识点，系统会结合当前课程知识图谱和你的学习画像规划路径。
          </p>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="例如：反向传播、CNN、强化学习"
            list="concept-suggestions"
            className="flex-1 rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
          />
          <datalist id="concept-suggestions">
            {conceptSuggestions.map((name) => (
              <option key={name} value={name} />
            ))}
          </datalist>
          <button
            onClick={handleCreate}
            disabled={generating || !goal.trim()}
            className="shrink-0 rounded-xl bg-[var(--color-terracotta)] px-6 py-3 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:opacity-50"
          >
            {generating ? "规划中..." : "生成路径"}
          </button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-[280px_minmax(0,1fr)]">
        {/* 路径列表 */}
        <div className="min-w-0 rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
          <h2 className="mb-3 text-sm font-medium text-[var(--color-warm-gray-700)]">
            我的学习路径
          </h2>
          {loading ? (
            <p className="py-4 text-center text-xs text-[var(--color-warm-gray-400)]">
              加载中...
            </p>
          ) : paths.length === 0 ? (
            <p className="py-4 text-center text-xs text-[var(--color-warm-gray-400)]">
              还没有学习路径，在上方创建一个吧
            </p>
          ) : (
            <div className="space-y-2">
              {paths.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => loadPath(p.id)}
                  className={`w-full rounded-lg px-3 py-2.5 text-left transition-colors ${
                    activePath?.id === p.id
                      ? "bg-[var(--color-terracotta)]/10 ring-1 ring-[var(--color-terracotta)]/30"
                      : "hover:bg-[var(--color-parchment)]"
                  }`}
                >
                  <div className="text-sm font-medium text-[var(--color-warm-gray-800)] line-clamp-1">
                    {p.title}
                  </div>
                  {p.course_id && (
                    <div className="mt-0.5 text-[10px] uppercase text-[var(--color-warm-gray-400)]">
                      {p.course_id}
                    </div>
                  )}
                  <div className="mt-1 flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-warm-gray-100)]">
                      <div
                        className="h-full rounded-full bg-[var(--color-terracotta)] transition-all"
                        style={{ width: `${Math.round(p.progress * 100)}%` }}
                      />
                    </div>
                    <span className="shrink-0 text-[11px] text-[var(--color-warm-gray-400)]">
                      {p.node_count} 个知识点
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 路径详情 */}
        <div className="min-w-0">
          {activePath ? (
            <>
              {/* 进度条 */}
              <div className="mb-4 rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="text-[var(--color-warm-gray-600)]">
                    {activePath.title}
                  </span>
                  <span className="font-medium text-[var(--color-terracotta)]">
                    {progress}%
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--color-warm-gray-100)]">
                  <div
                    className="h-full rounded-full bg-[var(--color-terracotta)] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                {recommendation && (
                  <p className="mt-2 text-xs text-[var(--color-warm-gray-500)]">
                    {recommendation.message}
                  </p>
                )}
              </div>

              <LearningPathGraph path={activePath} onToggleNode={toggleNodeStatus} />

              {/* 节点列表 */}
              <div className="relative">
                <div className="absolute bottom-0 left-6 top-0 w-0.5 bg-[var(--color-warm-gray-200)]" />
                <div className="space-y-4">
                  {activePath.nodes.map((node, idx) => {
                    const isLast = idx === activePath.nodes.length - 1;
                    const isCompleted = node.status === "completed";
                    return (
                      <div key={node.concept} className="relative flex gap-4 pl-3">
                        <button
                          type="button"
                          onClick={() => toggleNodeStatus(node)}
                          className={`relative z-10 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-2 transition-colors ${
                            isCompleted
                              ? "bg-[var(--color-terracotta)] text-white ring-[var(--color-terracotta)]"
                              : "bg-[var(--color-ivory)] text-[var(--color-warm-gray-400)] ring-[var(--color-warm-gray-200)]"
                          }`}
                        >
                          {isCompleted ? (
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          ) : (
                            <span className="text-[11px]">{idx + 1}</span>
                          )}
                        </button>
                        <div
                          className={`flex-1 rounded-xl px-4 py-3 ring-1 transition-colors ${
                            isLast
                              ? "bg-[var(--color-terracotta)]/5 ring-[var(--color-terracotta)]/30"
                              : isCompleted
                                ? "bg-[var(--color-warm-gray-50)] ring-[var(--color-warm-gray-100)]"
                                : "bg-[var(--color-ivory)] ring-[var(--color-warm-gray-200)]"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-sm font-medium ${
                                isLast ? "text-[var(--color-terracotta)]" : "text-[var(--color-warm-gray-800)]"
                              } ${isCompleted && !isLast ? "line-through opacity-60" : ""}`}
                            >
                              {node.concept}
                            </span>
                            {isLast && (
                              <span className="rounded-full bg-[var(--color-terracotta)] px-2 py-0.5 text-[10px] text-white">
                                目标
                              </span>
                            )}
                          </div>
                          {node.description && (
                            <p className="mt-1 text-xs leading-5 text-[var(--color-warm-gray-500)]">
                              {node.description}
                            </p>
                          )}
                          {node.chapter && (
                            <div className="mt-1.5 text-[11px] text-[var(--color-warm-gray-400)]">
                              {node.chapter} · {node.section}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center rounded-xl bg-[var(--color-ivory)] py-16 ring-1 ring-[var(--color-warm-gray-200)]">
              <div className="text-center">
                <p className="text-sm text-[var(--color-warm-gray-500)]">
                  {paths.length > 0
                    ? "选择左侧路径查看详情，或创建新路径"
                    : "输入目标知识点，生成个性化学习路径"}
                </p>
                <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
                  系统会基于知识图谱自动排列前置知识学习顺序
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
