"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { Profile } from "@/lib/types";

interface ProfileRadarChartProps {
  profile: Profile;
}

const CODING_LEVEL_MAP: Record<string, number> = {
  "零基础": 1,
  "入门": 2,
  "初级": 3,
  "中级": 4,
  "高级": 5,
  "专家": 5,
};

const PACE_MAP: Record<string, number> = {
  "很慢": 1,
  "慢": 2,
  "较慢": 2,
  "正常": 3,
  "适中": 3,
  "较快": 4,
  "快": 4,
  "很快": 5,
};

const RADAR_COLORS = {
  primary: "var(--color-terracotta)",
  tooltipBg: "var(--color-ivory)",
  tooltipBorder: "var(--color-warm-gray-200)",
};

function codingScore(level: string | null): number {
  if (!level) return 0;
  return CODING_LEVEL_MAP[level] ?? 2;
}

function paceScore(pace: string | null): number {
  if (!pace) return 0;
  return PACE_MAP[pace] ?? 3;
}

function knowledgeScore(kb: Record<string, string> | null): number {
  if (!kb || Object.keys(kb).length === 0) return 0;
  const levelScores: Record<string, number> = {
    "未学": 1, "了解": 2, "入门": 2, "初学": 2,
    "一般": 3, "掌握": 4, "熟练": 4, "精通": 5,
  };
  const values = Object.values(kb);
  const total = values.reduce((sum, v) => {
    const s = typeof v === "string" ? (levelScores[v] ?? 2) : 2;
    return sum + s;
  }, 0);
  return Math.min(5, Math.round((total / values.length) * 10) / 10);
}

function weeklyHoursScore(hours: number | null): number {
  if (hours === null || hours === undefined) return 0;
  if (hours <= 2) return 1;
  if (hours <= 5) return 2;
  if (hours <= 10) return 3;
  if (hours <= 20) return 4;
  return 5;
}

function awarenessScore(items: string[] | null): number {
  if (!items || items.length === 0) return 0;
  if (items.length === 1) return 2;
  if (items.length <= 3) return 3;
  if (items.length <= 5) return 4;
  return 5;
}

export function ProfileRadarChart({ profile }: ProfileRadarChartProps) {
  const data = [
    { dimension: "编程水平", value: codingScore(profile.coding_level), fullMark: 5 },
    { dimension: "学习投入", value: weeklyHoursScore(profile.weekly_hours), fullMark: 5 },
    { dimension: "知识基础", value: knowledgeScore(profile.knowledge_base), fullMark: 5 },
    { dimension: "学习节奏", value: paceScore(profile.learning_pace), fullMark: 5 },
    { dimension: "兴趣广度", value: awarenessScore(profile.interest_areas), fullMark: 5 },
    { dimension: "自我认知", value: awarenessScore(profile.weak_points), fullMark: 5 },
  ];

  const hasData = data.some((d) => d.value > 0);

  if (!hasData) {
    return (
      <div className="flex items-center justify-center rounded-xl bg-[var(--color-ivory)] ring-1 ring-[var(--color-warm-gray-200)] py-12">
        <p className="text-sm text-[var(--color-warm-gray-400)]">
          暂无足够数据生成画像雷达图，请先通过对话完善学习画像。
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-[var(--color-ivory)] ring-1 ring-[var(--color-warm-gray-200)] p-4">
      <h3 className="mb-2 text-sm font-medium text-[var(--color-warm-gray-700)] font-serif">
        学习画像雷达图
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="var(--color-warm-gray-200)" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 12, fill: "var(--color-warm-gray-600)" }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 5]}
            tick={{ fontSize: 10, fill: "var(--color-warm-gray-500)" }}
            tickCount={6}
          />
          <Radar
            name="画像"
            dataKey="value"
            stroke={RADAR_COLORS.primary}
            fill={RADAR_COLORS.primary}
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: RADAR_COLORS.tooltipBg,
              border: `1px solid ${RADAR_COLORS.tooltipBorder}`,
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value) => [`${value}/5`, "评分"]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
