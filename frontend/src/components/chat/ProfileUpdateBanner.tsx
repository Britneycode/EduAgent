"use client";

import { Check, X } from "lucide-react";
import type { ProfileUpdateProposedPayload } from "@/lib/types";

const PROFILE_FIELD_LABELS: Record<string, string> = {
  major: "专业",
  grade: "年级",
  knowledge_base: "知识基础",
  cognitive_style: "认知风格",
  learning_goal: "学习目标",
  weak_points: "薄弱点",
  learning_pace: "学习节奏",
  interest_areas: "兴趣方向",
  coding_level: "编程水平",
  weekly_hours: "每周学习时间",
};

interface ProfileUpdateBannerProps {
  proposal: ProfileUpdateProposedPayload;
  confirmState: "idle" | "saving" | "saved" | "error";
  confirmMessage: string | null;
  onConfirm: () => void;
  onDismiss: () => void;
}

export function ProfileUpdateBanner({
  proposal,
  confirmState,
  confirmMessage,
  onConfirm,
  onDismiss,
}: ProfileUpdateBannerProps) {
  return (
    <div className="mx-3 mb-3 rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-sm shadow-[var(--shadow-ring)]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="font-medium text-[var(--color-warm-gray-800)]">
            Agent 建议更新学习画像
          </p>
          <p className="mt-1 text-xs leading-5 text-[var(--color-warm-gray-600)]">
            变更项：
            {proposal.changed_fields
              .map((field) => PROFILE_FIELD_LABELS[field] ?? field)
              .join("、") || "画像字段"}
          </p>
          {confirmMessage && (
            <p
              className={`mt-1 text-xs ${
                confirmState === "error"
                  ? "text-red-600"
                  : "text-[var(--color-terracotta)]"
              }`}
            >
              {confirmMessage}
            </p>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={onConfirm}
            disabled={confirmState === "saving"}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-[var(--color-terracotta)] px-3 text-xs text-white hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Check className="h-3.5 w-3.5" />
            {confirmState === "saving" ? "保存中" : "确认"}
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] hover:text-[var(--color-terracotta)]"
          >
            <X className="h-3.5 w-3.5" />
            忽略
          </button>
        </div>
      </div>
    </div>
  );
}
