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
}

export function AgentStatus({ agent, message }: AgentStatusProps) {
  const label = AGENT_LABELS[agent] || agent;

  return (
    <div className="flex items-center gap-2 py-2 px-3 text-sm text-[var(--color-warm-gray-500)]">
      <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-terracotta)] animate-pulse" />
      {agent && (
        <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--color-warm-gray-100)] text-[var(--color-warm-gray-600)]">
          {label}
        </span>
      )}
      <span>{message}</span>
    </div>
  );
}
