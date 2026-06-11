"use client";

import { useState } from "react";
import { updateProfile } from "@/lib/api";

type FieldName = keyof WizardData;

const STEPS: { title: string; description: string; fields: FieldName[] }[] = [
  {
    title: "你的学习背景",
    description: "帮助我们了解你的专业和年级，提供更精准的学习内容",
    fields: ["major", "grade"],
  },
  {
    title: "学习目标",
    description: "明确你的目标，AI 会针对性地规划学习路径",
    fields: ["learning_goal", "weekly_hours"],
  },
  {
    title: "学习偏好",
    description: "了解你的学习风格和编程水平，调整教学方式",
    fields: ["cognitive_style", "coding_level", "learning_pace"],
  },
  {
    title: "薄弱与兴趣",
    description: "告诉 AI 你的薄弱点和兴趣方向，重点突破和拓展",
    fields: ["weak_points", "interest_areas"],
  },
];

const MAJORS = ["计算机科学", "软件工程", "人工智能", "数据科学", "电子信息", "数学", "自动化", "其他理工科", "文科", "不确定"];
const GRADES = ["大一", "大二", "大三", "大四", "研一", "研二", "研三", "已毕业", "自学"];
const GOALS = ["通过考试", "掌握实战技能", "了解领域概况", "完成课程作业", "准备面试", "兴趣爱好"];
const COGNITIVE_STYLES = ["视觉型（喜欢图表、导图）", "阅读型（喜欢文档、讲义）", "动手型（喜欢代码、实验）", "听觉型（喜欢讲解、讨论）"];
const PACES = ["快速（想快速过一遍）", "适中（按部就班）", "细致（每个点都要搞懂）"];
const CODING_LEVELS = ["零基础", "入门（写过简单代码）", "熟悉（能独立完成项目）", "精通"];
const INTERESTS = ["机器学习", "深度学习", "自然语言处理", "计算机视觉", "强化学习", "数据分析", "Web开发", "算法与数据结构"];

interface WizardData {
  major: string;
  grade: string;
  learning_goal: string;
  cognitive_style: string;
  learning_pace: string;
  coding_level: string;
  weekly_hours: number;
  weak_points: string;
  interest_areas: string;
}

export function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState<WizardData>({
    major: "", grade: "", learning_goal: "", cognitive_style: "",
    learning_pace: "", coding_level: "", weekly_hours: 6,
    weak_points: "", interest_areas: "",
  });

  const update = (key: keyof WizardData, value: string | number) => {
    setData((prev) => ({ ...prev, [key]: value }));
  };

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep((s) => s + 1);
    } else {
      handleSave();
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({
        major: data.major || null,
        grade: data.grade || null,
        learning_goal: data.learning_goal || null,
        cognitive_style: data.cognitive_style || null,
        learning_pace: data.learning_pace || null,
        coding_level: data.coding_level || null,
        weekly_hours: data.weekly_hours || null,
        weak_points: data.weak_points ? data.weak_points.split(/[,，、]/).map((s) => s.trim()).filter(Boolean) : [],
        interest_areas: data.interest_areas ? data.interest_areas.split(/[,，、]/).map((s) => s.trim()).filter(Boolean) : [],
      });
    } catch {}
    setSaving(false);
    onComplete();
  };

  const currentStep = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="rounded-2xl bg-[var(--color-ivory)] p-6 ring-1 ring-[var(--color-warm-gray-200)]">
      {/* 进度条 */}
      <div className="mb-6 flex gap-1">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i <= step ? "bg-[var(--color-terracotta)]" : "bg-[var(--color-warm-gray-200)]"
            }`}
          />
        ))}
      </div>

      <h2 className="mb-1 font-serif text-xl text-[var(--color-warm-gray-800)]">
        {currentStep.title}
      </h2>
      <p className="mb-6 text-sm text-[var(--color-warm-gray-500)]">
        {currentStep.description}
      </p>

      <div className="space-y-4">
        {currentStep.fields.includes("major") && (
          <ChoiceGroup label="专业" options={MAJORS} value={data.major} onChange={(v) => update("major", v)} />
        )}
        {currentStep.fields.includes("grade") && (
          <ChoiceGroup label="年级" options={GRADES} value={data.grade} onChange={(v) => update("grade", v)} />
        )}
        {currentStep.fields.includes("learning_goal") && (
          <ChoiceGroup label="学习目标" options={GOALS} value={data.learning_goal} onChange={(v) => update("learning_goal", v)} />
        )}
        {currentStep.fields.includes("cognitive_style") && (
          <ChoiceGroup label="学习风格" options={COGNITIVE_STYLES} value={data.cognitive_style} onChange={(v) => update("cognitive_style", v)} />
        )}
        {currentStep.fields.includes("learning_pace") && (
          <ChoiceGroup label="学习节奏" options={PACES} value={data.learning_pace} onChange={(v) => update("learning_pace", v)} />
        )}
        {currentStep.fields.includes("coding_level") && (
          <ChoiceGroup label="编程水平" options={CODING_LEVELS} value={data.coding_level} onChange={(v) => update("coding_level", v)} />
        )}
        {currentStep.fields.includes("weekly_hours") && (
          <div>
            <label className="mb-2 block text-sm text-[var(--color-warm-gray-600)]">每周可投入时间（小时）</label>
            <input
              type="range" min={1} max={40} value={data.weekly_hours}
              onChange={(e) => update("weekly_hours", Number(e.target.value))}
              className="w-full accent-[var(--color-terracotta)]"
            />
            <p className="mt-1 text-center text-sm text-[var(--color-terracotta)]">{data.weekly_hours} 小时/周</p>
          </div>
        )}
        {currentStep.fields.includes("weak_points") && (
          <div>
            <label className="mb-2 block text-sm text-[var(--color-warm-gray-600)]">薄弱知识点（用逗号分隔）</label>
            <input
              type="text" value={data.weak_points}
              onChange={(e) => update("weak_points", e.target.value)}
              placeholder="例如：反向传播, 梯度下降, CNN"
              className="w-full rounded-lg bg-[var(--color-parchment)] px-4 py-2.5 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            />
          </div>
        )}
        {currentStep.fields.includes("interest_areas") && (
          <div>
            <label className="mb-2 block text-sm text-[var(--color-warm-gray-600)]">感兴趣的方向（多选）</label>
            <div className="flex flex-wrap gap-2">
              {INTERESTS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    const current = data.interest_areas.split(/[,，、]/).map((s) => s.trim()).filter(Boolean);
                    const next = current.includes(item) ? current.filter((i) => i !== item) : [...current, item];
                    update("interest_areas", next.join("、"));
                  }}
                  className={`rounded-full px-3 py-1.5 text-xs ring-1 transition-all ${
                    data.interest_areas.includes(item)
                      ? "bg-[var(--color-terracotta)]/10 text-[var(--color-terracotta)] ring-[var(--color-terracotta)]"
                      : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-600)] ring-[var(--color-warm-gray-200)] hover:ring-[var(--color-terracotta)]/40"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="rounded-lg px-4 py-2 text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] disabled:opacity-30"
        >
          ← 上一步
        </button>
        <span className="text-xs text-[var(--color-warm-gray-400)]">
          {step + 1} / {STEPS.length}
        </span>
        <button
          type="button"
          onClick={handleNext}
          disabled={saving}
          className="rounded-lg bg-[var(--color-terracotta)] px-6 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:opacity-50"
        >
          {saving ? "保存中..." : isLast ? "完成 →" : "下一步 →"}
        </button>
      </div>
    </div>
  );
}

function ChoiceGroup({
  label, options, value, onChange,
}: {
  label: string; options: string[]; value: string; onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-2 block text-sm text-[var(--color-warm-gray-600)]">{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={`rounded-full px-3 py-1.5 text-xs ring-1 transition-all ${
              value === opt
                ? "bg-[var(--color-terracotta)]/10 text-[var(--color-terracotta)] ring-[var(--color-terracotta)]"
                : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-600)] ring-[var(--color-warm-gray-200)] hover:ring-[var(--color-terracotta)]/40"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
