"use client";

import {
  BookOpenText,
  BrainCircuit,
  CheckCircle2,
  Code2,
  FileQuestion,
  Film,
  GitBranch,
  Loader2,
  MessageCircle,
  Newspaper,
  Route,
} from "lucide-react";
import type { AgentTimelineItem } from "@/store/chatStreamStore";
import type { ProgressPayload, ResourceCard } from "@/lib/types";

type FlowState = "active" | "done";

export interface AgentFlowStep {
  agent: string;
  label: string;
  message: string;
  state: FlowState;
  resourceCount: number;
}

const AGENT_META: Record<string, { label: string; role: string }> = {
  RouterAgent: { label: "Router", role: "意图识别" },
  ProfileAgent: { label: "Profile", role: "画像更新" },
  PlannerAgent: { label: "Planner", role: "任务拆解" },
  TutorAgent: { label: "Tutor", role: "即时答疑" },
  DocAgent: { label: "Doc", role: "讲义生成" },
  QuizAgent: { label: "Quiz", role: "练习生成" },
  CodeAgent: { label: "Code", role: "代码实践" },
  MediaAgent: { label: "Media", role: "多模态资源" },
  ReadingAgent: { label: "Reading", role: "拓展阅读" },
  VideoAgent: { label: "Video", role: "相关视频" },
};

const AGENT_ICONS = {
  RouterAgent: GitBranch,
  ProfileAgent: BrainCircuit,
  PlannerAgent: Route,
  TutorAgent: MessageCircle,
  DocAgent: BookOpenText,
  QuizAgent: FileQuestion,
  CodeAgent: Code2,
  MediaAgent: Film,
  ReadingAgent: Newspaper,
  VideoAgent: Film,
};

const AGENT_ORDER = [
  "RouterAgent",
  "ProfileAgent",
  "PlannerAgent",
  "TutorAgent",
  "DocAgent",
  "QuizAgent",
  "CodeAgent",
  "MediaAgent",
  "ReadingAgent",
  "VideoAgent",
];

const RESOURCE_AGENT_FALLBACK: Record<ResourceCard["resource_type"], string> = {
  document: "DocAgent",
  quiz: "QuizAgent",
  code: "CodeAgent",
  mindmap: "MediaAgent",
  ppt: "MediaAgent",
  ppt_images: "MediaAgent",
  animation: "MediaAgent",
  video: "VideoAgent",
  reading: "ReadingAgent",
};

function labelForAgent(agent: string): string {
  return AGENT_META[agent]?.label ?? agent;
}

function roleForAgent(agent: string): string {
  return AGENT_META[agent]?.role ?? "协作节点";
}

export function buildAgentFlowSteps(
  timeline: AgentTimelineItem[],
  resources: ResourceCard[],
  isStreaming: boolean
): AgentFlowStep[] {
  const stepMap = new Map<string, AgentFlowStep>();
  const resourceAgents = new Set<string>();

  for (const item of timeline) {
    if (!item.agent) continue;
    stepMap.set(item.agent, {
      agent: item.agent,
      label: labelForAgent(item.agent),
      message: item.message || roleForAgent(item.agent),
      state: "done",
      resourceCount: 0,
    });
  }

  for (const resource of resources) {
    const agent =
      resource.agent_name ?? RESOURCE_AGENT_FALLBACK[resource.resource_type];
    resourceAgents.add(agent);
    const existing = stepMap.get(agent);
    const nextCount = (existing?.resourceCount ?? 0) + 1;
    stepMap.set(agent, {
      agent,
      label: labelForAgent(agent),
      message:
        nextCount > 1
          ? `已生成 ${nextCount} 个资源`
          : `已生成：${resource.title}`,
      state: "done",
      resourceCount: nextCount,
    });
  }

  const lastTimelineAgent = timeline.at(-1)?.agent;
  if (isStreaming && lastTimelineAgent && !resourceAgents.has(lastTimelineAgent)) {
    const current = stepMap.get(lastTimelineAgent);
    if (current) {
      stepMap.set(lastTimelineAgent, { ...current, state: "active" });
    }
  }

  return [...stepMap.values()].sort((a, b) => {
    const aIndex = AGENT_ORDER.indexOf(a.agent);
    const bIndex = AGENT_ORDER.indexOf(b.agent);
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
  });
}

interface AgentFlowProps {
  timeline: AgentTimelineItem[];
  resources: ResourceCard[];
  isStreaming: boolean;
  progress?: ProgressPayload | null;
}

export function AgentFlow({ timeline, resources, isStreaming, progress }: AgentFlowProps) {
  const steps = buildAgentFlowSteps(timeline, resources, isStreaming);
  if (steps.length === 0) return null;

  return (
    <div className="mx-3 mb-3 rounded-2xl bg-[var(--color-parchment)] px-3 py-3 shadow-[var(--shadow-ring)]">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="font-serif text-sm font-medium text-[var(--color-warm-gray-700)]">
          Agent 协作链路
        </h2>
        <span className="text-[11px] text-[var(--color-warm-gray-400)]">
          {progress && progress.total > 0
            ? `${progress.completed}/${progress.total} · ${progress.percent}%`
            : `${steps.length} 个节点`}
        </span>
      </div>
      {progress && progress.total > 0 && (
        <div className="mb-2">
          <div className="mb-1 flex items-center justify-between gap-2 text-[11px] text-[var(--color-warm-gray-600)]">
            <span className="truncate">{progress.message}</span>
            <span>{progress.percent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[var(--color-warm-gray-200)]">
            <div
              className="h-full rounded-full bg-[var(--color-terracotta)] transition-[width]"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        </div>
      )}
      <div className="overflow-x-auto">
        <ol className="flex min-w-max items-stretch gap-2">
          {steps.map((step, index) => {
            const Icon = AGENT_ICONS[step.agent as keyof typeof AGENT_ICONS] ?? GitBranch;
            return (
            <li key={step.agent} className="flex items-center gap-2">
              <div
                className={`h-[82px] w-40 rounded-xl px-3 py-2 ring-1 transition-colors ${
                  step.state === "active"
                    ? "bg-[var(--color-terracotta)] text-white ring-[var(--color-terracotta)]"
                    : "bg-[var(--color-ivory)] text-[var(--color-warm-gray-700)] ring-[var(--color-warm-gray-200)]"
                }`}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="inline-flex min-w-0 items-center gap-1.5">
                    <Icon className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate text-xs font-medium">
                    {step.label}
                    </span>
                  </span>
                  {step.state === "active" ? (
                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                  ) : (
                    <CheckCircle2
                      className="h-3.5 w-3.5 shrink-0 text-[var(--color-terracotta)]"
                    />
                  )}
                </div>
                <p
                  className={`mb-1 truncate text-[11px] ${
                    step.state === "active"
                      ? "text-white/75"
                      : "text-[var(--color-warm-gray-400)]"
                  }`}
                >
                  {roleForAgent(step.agent)}
                </p>
                <p className="line-clamp-2 text-[11px] leading-4">
                  {step.message}
                </p>
              </div>
              {index < steps.length - 1 && (
                <span className="h-px w-5 bg-[var(--color-warm-gray-300)]" />
              )}
            </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
