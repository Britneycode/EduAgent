"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchAgentObservability,
  fetchLearningDashboard,
  fetchReviewQueue,
  updateReviewItem,
} from "@/lib/api";
import type {
  AgentObservability,
  LearningDashboard,
  LearningActivity,
  ReviewItem,
} from "@/lib/types";

const ACTIVITY_LABELS: Record<string, string> = {
  quiz: "测验",
  resource_view: "资源学习",
  code_practice: "代码实践",
  note: "笔记",
};

const LEVEL_LABELS: Record<string, string> = {
  mastered: "已掌握",
  in_progress: "巩固中",
  weak: "需复习",
  unknown: "暂无数据",
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  choice: "选择",
  judge: "判断",
  short_answer: "简答",
};

const CHART_COLORS = {
  primary: "var(--color-terracotta)",
  secondary: "var(--color-resource-mindmap)",
  bar: "var(--color-resource-reading)",
  grid: "var(--color-warm-gray-200)",
  tick: "var(--color-warm-gray-600)",
  label: "var(--color-warm-gray-800)",
  tooltipBg: "var(--color-ivory)",
  tooltipBorder: "var(--color-warm-gray-200)",
};

function formatDuration(seconds: number): string {
  if (!seconds) return "0 分钟";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`;
}

function formatMilliseconds(ms: number): string {
  if (!ms) return "0 ms";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function formatDateLabel(date: string): string {
  const parts = date.split("-");
  return parts.length === 3 ? `${Number(parts[1])}/${Number(parts[2])}` : date;
}

function activityLabel(activity: LearningActivity): string {
  const label = ACTIVITY_LABELS[activity.activity_type] ?? activity.activity_type;
  return activity.knowledge_point ? `${label} · ${activity.knowledge_point}` : label;
}

export default function AnalyticsPage() {
  const [dashboard, setDashboard] = useState<LearningDashboard | null>(null);
  const [agentObservability, setAgentObservability] =
    useState<AgentObservability | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingReviewId, setUpdatingReviewId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      fetchLearningDashboard(),
      fetchReviewQueue(6),
      fetchAgentObservability(80),
    ])
      .then(([data, queue, agentData]) => {
        setDashboard(data);
        setAgentObservability(agentData);
        setReviewItems(queue);
        setError(null);
      })
      .catch((err) => {
        setDashboard(null);
        setAgentObservability(null);
        setReviewItems([]);
        setError(err instanceof Error ? err.message : "获取学习评估数据失败");
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleReviewUpdate(itemId: number, mastered: boolean) {
    if (updatingReviewId) return;
    setUpdatingReviewId(itemId);
    try {
      const updated = await updateReviewItem(itemId, mastered);
      setReviewItems((items) =>
        updated.status === "mastered" || updated.next_review_at
          ? items.filter((item) => item.id !== itemId)
          : items.map((item) => (item.id === itemId ? updated : item))
      );
      setDashboard((current) =>
        current
          ? {
              ...current,
              summary: {
                ...current.summary,
                pending_review_count: Math.max(
                  0,
                  current.summary.pending_review_count - 1
                ),
              },
            }
          : current
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新复习状态失败");
    } finally {
      setUpdatingReviewId(null);
    }
  }

  const trendData = useMemo(
    () =>
      (dashboard?.activity_trend ?? []).map((item) => ({
        ...item,
        label: formatDateLabel(item.date),
        minutes: Math.round(item.duration_sec / 60),
      })),
    [dashboard]
  );

  const pathCompletion =
    dashboard && dashboard.summary.total_nodes > 0
      ? Math.round((dashboard.summary.completed_nodes / dashboard.summary.total_nodes) * 100)
      : 0;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-serif text-2xl text-[var(--color-warm-gray-800)]">
              学习效果评估
            </h1>
            <p className="mt-1 text-sm text-[var(--color-warm-gray-500)]">
              汇总测验、学习时长和路径进度，定位下一步最值得投入的知识点。
            </p>
          </div>
          {dashboard && (
            <div className="text-xs text-[var(--color-warm-gray-400)]">
              最近 7 天学习活动
            </div>
          )}
        </div>

        {loading ? (
          <div className="rounded-xl bg-[var(--color-ivory)] p-8 text-center text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
            正在整理学习数据...
          </div>
        ) : error ? (
          <div className="rounded-xl bg-red-50 p-5 text-sm text-red-700 ring-1 ring-red-100">
            {error}
          </div>
        ) : dashboard ? (
          <div className="space-y-6">
            <section className="grid gap-3 md:grid-cols-3 lg:grid-cols-5">
              <MetricPanel
                label="学习时长"
                value={formatDuration(dashboard.summary.total_duration_sec)}
                hint={`${dashboard.summary.total_activities} 次记录`}
              />
              <MetricPanel
                label="测验均分"
                value={`${dashboard.summary.average_quiz_score.toFixed(1)} 分`}
                hint={`${dashboard.summary.quiz_count} 次测验`}
              />
              <MetricPanel
                label="路径完成"
                value={`${pathCompletion}%`}
                hint={`${dashboard.summary.completed_nodes}/${dashboard.summary.total_nodes} 个节点`}
              />
              <MetricPanel
                label="活跃路径"
                value={`${dashboard.summary.active_paths}`}
                hint="正在推进的学习目标"
              />
              <MetricPanel
                label="待复习"
                value={`${dashboard.summary.pending_review_count}`}
                hint="错题队列"
              />
            </section>

            <Panel title="Agent 可观测" subtitle="记录每轮编排中的节点耗时、状态、模型调用和资源类型">
              {agentObservability && agentObservability.summary.total_events > 0 ? (
                <div className="space-y-5">
                  <div className="grid gap-3 md:grid-cols-4">
                    <div className="rounded-lg bg-[var(--color-parchment)] px-3 py-3 ring-1 ring-[var(--color-warm-gray-200)]">
                      <div className="text-[11px] text-[var(--color-warm-gray-400)]">
                        最近运行
                      </div>
                      <div className="mt-1 text-lg font-medium text-[var(--color-warm-gray-800)]">
                        {agentObservability.summary.total_runs}
                      </div>
                    </div>
                    <div className="rounded-lg bg-[var(--color-parchment)] px-3 py-3 ring-1 ring-[var(--color-warm-gray-200)]">
                      <div className="text-[11px] text-[var(--color-warm-gray-400)]">
                        节点事件
                      </div>
                      <div className="mt-1 text-lg font-medium text-[var(--color-warm-gray-800)]">
                        {agentObservability.summary.total_events}
                      </div>
                    </div>
                    <div className="rounded-lg bg-[var(--color-parchment)] px-3 py-3 ring-1 ring-[var(--color-warm-gray-200)]">
                      <div className="text-[11px] text-[var(--color-warm-gray-400)]">
                        平均耗时
                      </div>
                      <div className="mt-1 text-lg font-medium text-[var(--color-warm-gray-800)]">
                        {formatMilliseconds(agentObservability.summary.average_duration_ms)}
                      </div>
                    </div>
                    <div className="rounded-lg bg-[var(--color-parchment)] px-3 py-3 ring-1 ring-[var(--color-warm-gray-200)]">
                      <div className="text-[11px] text-[var(--color-warm-gray-400)]">
                        错误事件
                      </div>
                      <div className="mt-1 text-lg font-medium text-[var(--color-terracotta)]">
                        {agentObservability.summary.error_events}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
                    <div>
                      <h3 className="mb-3 text-sm font-medium text-[var(--color-warm-gray-700)]">
                        Agent 耗时排行
                      </h3>
                      <div className="space-y-3">
                        {agentObservability.agent_stats.slice(0, 6).map((agent) => (
                          <div key={agent.agent_name}>
                            <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                              <span className="font-medium text-[var(--color-warm-gray-700)]">
                                {agent.agent_name}
                              </span>
                              <span className="text-[var(--color-warm-gray-400)]">
                                {agent.call_count} 次 · 均值 {formatMilliseconds(agent.average_duration_ms)}
                              </span>
                            </div>
                            <div className="h-2 overflow-hidden rounded-full bg-[var(--color-warm-gray-100)]">
                              <div
                                className="h-full rounded-full bg-[#6f8f7a]"
                                style={{
                                  width: `${Math.min(
                                    100,
                                    Math.max(8, agent.average_duration_ms / 20)
                                  )}%`,
                                }}
                              />
                            </div>
                            {agent.resource_types.length > 0 && (
                              <div className="mt-1 text-[11px] text-[var(--color-warm-gray-400)]">
                                {agent.resource_types.join(" / ")}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h3 className="mb-3 text-sm font-medium text-[var(--color-warm-gray-700)]">
                        最近运行链路
                      </h3>
                      <div className="space-y-2">
                        {agentObservability.recent_runs.slice(0, 5).map((run) => (
                          <div
                            key={run.run_id}
                            className="rounded-lg bg-[var(--color-parchment)] px-3 py-2 ring-1 ring-[var(--color-warm-gray-200)]"
                          >
                            <div className="flex items-center justify-between gap-3 text-xs">
                              <span className="font-medium text-[var(--color-warm-gray-700)]">
                                {run.status === "error" ? "异常" : "完成"}
                              </span>
                              <span className="text-[var(--color-warm-gray-400)]">
                                {formatMilliseconds(run.duration_ms)}
                              </span>
                            </div>
                            <div className="mt-1 line-clamp-1 text-[11px] text-[var(--color-warm-gray-500)]">
                              {run.agents.join(" → ")}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-3 text-sm font-medium text-[var(--color-warm-gray-700)]">
                      最近节点事件
                    </h3>
                    <div className="overflow-x-auto rounded-lg ring-1 ring-[var(--color-warm-gray-200)]">
                      <div className="min-w-[520px]">
                        <div className="grid grid-cols-[1fr_1fr_90px_90px] bg-[var(--color-parchment)] px-3 py-2 text-[11px] text-[var(--color-warm-gray-400)]">
                          <span>Agent</span>
                          <span>节点</span>
                          <span>耗时</span>
                          <span>状态</span>
                        </div>
                        {agentObservability.recent_events.slice(0, 8).map((event) => (
                          <div
                            key={event.id}
                            className="grid grid-cols-[1fr_1fr_90px_90px] border-t border-[var(--color-warm-gray-200)] px-3 py-2 text-xs text-[var(--color-warm-gray-600)]"
                          >
                            <span className="truncate">{event.agent_name}</span>
                            <span className="truncate">
                              {event.resource_type || event.node_name}
                            </span>
                            <span>{formatMilliseconds(event.duration_ms)}</span>
                            <span
                              className={
                                event.status === "error"
                                  ? "text-[var(--color-terracotta)]"
                                  : "text-[#6f8f7a]"
                              }
                            >
                              {event.status === "error" ? "error" : "success"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyText text="暂无 Agent 运行记录。发送一次对话后，这里会展示 Router、Planner 和资源 Agent 的耗时与状态。" />
              )}
            </Panel>

            <Panel title="今日错题复习" subtitle="答错题会自动进入队列，复盘后可标记掌握">
              {reviewItems.length > 0 ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {reviewItems.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-lg bg-[var(--color-parchment)] p-3 ring-1 ring-[var(--color-warm-gray-200)]"
                    >
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-[var(--color-warm-gray-800)] px-2 py-0.5 text-[11px] text-white">
                          {QUESTION_TYPE_LABELS[item.question_type] ?? item.question_type}
                        </span>
                        {item.knowledge_point && (
                          <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                            {item.knowledge_point}
                          </span>
                        )}
                        <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                          复习 {item.review_count} 次
                        </span>
                      </div>
                      <p className="text-sm leading-6 text-[var(--color-warm-gray-800)]">
                        {item.question_text}
                      </p>
                      <div className="mt-2 grid gap-2 text-xs leading-5 text-[var(--color-warm-gray-600)] md:grid-cols-2">
                        <div className="rounded-md bg-[var(--color-ivory)] px-2 py-1">
                          你的答案：{item.user_answer || "未作答"}
                        </div>
                        <div className="rounded-md bg-[var(--color-ivory)] px-2 py-1">
                          正确答案：{item.correct_answer}
                        </div>
                      </div>
                      {item.explanation && (
                        <p className="mt-2 text-xs leading-5 text-[var(--color-warm-gray-500)]">
                          {item.explanation}
                        </p>
                      )}
                      <div className="mt-3 flex flex-wrap justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => void handleReviewUpdate(item.id, false)}
                          disabled={updatingReviewId === item.id}
                          className="rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          稍后再复习
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleReviewUpdate(item.id, true)}
                          disabled={updatingReviewId === item.id}
                          className="rounded-lg bg-[var(--color-terracotta)] px-3 py-1.5 text-xs text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          标记掌握
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyText text="暂无到期错题。提交测验后，答错题会出现在这里。" />
              )}
            </Panel>

            <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
              <Panel title="学习趋势" subtitle="活动数量、学习时长与测验均分">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData} margin={{ left: -20, right: 12, top: 8 }}>
                      <defs>
                        <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.35} />
                          <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" />
                      <XAxis dataKey="label" tick={{ fontSize: 12, fill: CHART_COLORS.tick }} />
                      <YAxis tick={{ fontSize: 12, fill: CHART_COLORS.tick }} allowDecimals={false} />
                      <Tooltip
                        formatter={(value, name) => [
                          value,
                          name === "activity_count" ? "活动" : name === "minutes" ? "分钟" : "均分",
                        ]}
                        contentStyle={{
                          backgroundColor: CHART_COLORS.tooltipBg,
                          border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                          borderRadius: "8px",
                        }}
                        labelStyle={{ color: CHART_COLORS.label }}
                      />
                      <Area
                        type="monotone"
                        dataKey="activity_count"
                        stroke={CHART_COLORS.primary}
                        fill="url(#activityFill)"
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="minutes"
                        stroke={CHART_COLORS.secondary}
                        fill="transparent"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Panel>

              <Panel title="下一步建议" subtitle="基于测验与路径进度">
                {dashboard.recommendations.length > 0 ? (
                  <div className="space-y-3">
                    {dashboard.recommendations.map((item) => (
                      <div
                        key={item}
                        className="rounded-lg bg-[var(--color-parchment)] px-3 py-3 text-sm leading-6 text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)]"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyText text="完成一次测验或学习活动后，这里会生成更具体的建议。" />
                )}
              </Panel>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <Panel title="知识点掌握" subtitle="按低分优先排序，便于定位薄弱点">
                {dashboard.knowledge_mastery.length > 0 ? (
                  <div className="space-y-3">
                    {dashboard.knowledge_mastery.map((item) => (
                      <div key={item.knowledge_point}>
                        <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                          <span className="font-medium text-[var(--color-warm-gray-800)]">
                            {item.knowledge_point}
                          </span>
                          <span className="text-xs text-[var(--color-warm-gray-400)]">
                            {LEVEL_LABELS[item.level]} · {item.attempts} 次
                          </span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-warm-gray-100)]">
                          <div
                            className={`h-full rounded-full ${item.average_score >= 85 ? "bg-[#6f8f7a]" : item.average_score >= 60 ? "bg-[#c7a35f]" : "bg-[var(--color-terracotta)]"}`}
                            style={{ width: `${Math.max(6, item.average_score)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyText text="提交练习题后会显示每个知识点的掌握情况。" />
                )}
              </Panel>

              <Panel title="活动结构" subtitle="学习行为类型分布">
                {dashboard.activity_types.length > 0 ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dashboard.activity_types} margin={{ left: -20, right: 12 }}>
                        <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" />
                        <XAxis
                          dataKey="activity_type"
                          tickFormatter={(value) => ACTIVITY_LABELS[value] ?? value}
                          tick={{ fontSize: 12, fill: CHART_COLORS.tick }}
                        />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: CHART_COLORS.tick }} />
                        <Tooltip
                          formatter={(value) => [value, "次数"]}
                          labelFormatter={(value) => ACTIVITY_LABELS[String(value)] ?? value}
                          contentStyle={{
                            backgroundColor: CHART_COLORS.tooltipBg,
                            border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                            borderRadius: "8px",
                          }}
                          labelStyle={{ color: CHART_COLORS.label }}
                        />
                        <Bar dataKey="count" fill={CHART_COLORS.bar} radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <EmptyText text="暂无学习活动记录。" />
                )}
              </Panel>
            </section>

            <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
              <Panel title="学习路径进度" subtitle="最近创建或更新的路径">
                {dashboard.path_progress.length > 0 ? (
                  <div className="space-y-3">
                    {dashboard.path_progress.map((path) => (
                      <div key={path.path_id} className="rounded-lg bg-[var(--color-parchment)] p-3 ring-1 ring-[var(--color-warm-gray-200)]">
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="line-clamp-1 text-sm font-medium text-[var(--color-warm-gray-800)]">
                              {path.title}
                            </div>
                            <div className="text-xs text-[var(--color-warm-gray-400)]">
                              目标：{path.goal_topic}
                            </div>
                          </div>
                          <span className="text-sm font-medium text-[var(--color-terracotta)]">
                            {Math.round(path.progress * 100)}%
                          </span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-warm-gray-100)]">
                          <div
                            className="h-full rounded-full bg-[var(--color-terracotta)]"
                            style={{ width: `${Math.round(path.progress * 100)}%` }}
                          />
                        </div>
                        <div className="mt-2 text-xs text-[var(--color-warm-gray-400)]">
                          {path.completed_count}/{path.total_count} 个知识点完成
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyText text="创建学习路径后会显示路径完成度。" />
                )}
              </Panel>

              <Panel title="近期活动" subtitle="最近 8 条学习记录">
                {dashboard.recent_activities.length > 0 ? (
                  <div className="divide-y divide-[var(--color-warm-gray-200)]">
                    {dashboard.recent_activities.map((activity) => (
                      <div key={activity.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                        <div className="min-w-0">
                          <div className="line-clamp-1 text-sm text-[var(--color-warm-gray-800)]">
                            {activityLabel(activity)}
                          </div>
                          <div className="mt-0.5 text-xs text-[var(--color-warm-gray-400)]">
                            {new Date(activity.created_at).toLocaleString("zh-CN")}
                            {activity.duration_sec ? ` · ${formatDuration(activity.duration_sec)}` : ""}
                          </div>
                        </div>
                        {activity.score !== null && activity.score !== undefined && (
                          <span className="shrink-0 rounded-full bg-[var(--color-terracotta)]/10 px-2 py-1 text-xs font-medium text-[var(--color-terracotta)]">
                            {activity.score.toFixed(0)} 分
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyText text="暂无近期活动。" />
                )}
              </Panel>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MetricPanel({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="text-xs text-[var(--color-warm-gray-400)]">{label}</div>
      <div className="mt-2 text-2xl font-medium text-[var(--color-warm-gray-800)]">
        {value}
      </div>
      <div className="mt-1 text-xs text-[var(--color-warm-gray-500)]">{hint}</div>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-4">
        <h2 className="text-base font-medium text-[var(--color-warm-gray-800)]">
          {title}
        </h2>
        <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return (
    <div className="rounded-lg bg-[var(--color-parchment)] px-4 py-8 text-center text-sm text-[var(--color-warm-gray-400)] ring-1 ring-[var(--color-warm-gray-200)]">
      {text}
    </div>
  );
}
