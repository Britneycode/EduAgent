import type { Profile } from "@/lib/types";

interface ProfileSummaryProps {
  profile: Profile;
}

const DIMENSION_LABELS: Record<string, string> = {
  major: "专业",
  grade: "年级",
  learning_goal: "学习目标",
  cognitive_style: "认知风格",
  learning_pace: "学习节奏",
  coding_level: "编程水平",
  weekly_hours: "每周学习时间",
  knowledge_base: "知识基础",
  weak_points: "薄弱环节",
  interest_areas: "兴趣领域",
};

function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "暂未提供";
  if (key === "weekly_hours" && typeof value === "number") return `${value} 小时/周`;
  if (key === "knowledge_base" && typeof value === "object") {
    const kb = value as Record<string, unknown>;
    if (kb.subject && kb.level) return `${String(kb.subject)}（${String(kb.level)}）`;
    if (kb.subject) return String(kb.subject);
    if (kb.level) return String(kb.level);
    if (Object.keys(kb).length === 0) return "暂未提供";
    return Object.entries(kb)
      .map(([concept, level]) => {
        if (level && typeof level === "object" && "level" in level) {
          const nested = level as Record<string, unknown>;
          return `${concept}（${String(nested.level)}）`;
        }
        return level ? `${concept}（${String(level)}）` : concept;
      })
      .join("、");
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join("、") : "暂未提供";
  }
  if (typeof value === "string") return value || "暂未提供";
  return String(value);
}

export function ProfileSummary({ profile }: ProfileSummaryProps) {
  const dimensions = [
    "major",
    "grade",
    "learning_goal",
    "cognitive_style",
    "knowledge_base",
    "learning_pace",
    "coding_level",
    "weekly_hours",
    "weak_points",
    "interest_areas",
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {dimensions.map((key) => {
        const value = profile[key as keyof Profile];
        const label = DIMENSION_LABELS[key] || key;
        const display = formatValue(key, value);
        const isEmpty = display === "暂未提供";

        return (
          <div
            key={key}
            className="rounded-xl bg-[var(--color-ivory)] ring-1 ring-[var(--color-warm-gray-200)] px-4 py-3"
          >
            <div className="text-xs text-[var(--color-warm-gray-400)] mb-1">
              {label}
            </div>
            <div
              className={`text-sm ${
                isEmpty
                  ? "text-[var(--color-warm-gray-300)] italic"
                  : "text-[var(--color-warm-gray-700)]"
              }`}
            >
              {display}
            </div>
          </div>
        );
      })}
    </div>
  );
}
