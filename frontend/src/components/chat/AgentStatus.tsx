import { Loader2 } from "lucide-react";

const AGENT_LABELS: Record<string, string> = {
  RouterAgent: "路由",
  ProfileAgent: "画像",
  PlannerAgent: "规划",
  DocAgent: "文档",
  QuizAgent: "题目",
  CodeAgent: "代码",
  TutorAgent: "辅导",
  MediaAgent: "媒体",
};

interface AgentStatusProps {
  agent: string;
  message: string;
  progress?: {
    completed: number;
    total: number;
    percent: number;
  } | null;
}

export function AgentStatus({ agent, message, progress }: AgentStatusProps) {
  const label = AGENT_LABELS[agent] || agent;

  return (
    <div className="px-3 py-2 text-sm text-[var(--color-warm-gray-600)]">
      <div className="flex items-center gap-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--color-terracotta)]" />
        {agent && (
          <span className="rounded bg-[var(--color-warm-gray-100)] px-1.5 py-0.5 text-xs text-[var(--color-warm-gray-700)]">
            {label}
          </span>
        )}
        <span>{message}</span>
      </div>
      {progress && progress.total > 0 && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-warm-gray-200)]">
          <div
            className="h-full rounded-full bg-[var(--color-terracotta)] transition-[width]"
            style={{ width: `${progress.percent}%` }}
          />
        </div>
      )}
    </div>
  );
}
