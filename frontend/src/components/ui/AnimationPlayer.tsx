"use client";

import { useEffect, useMemo, useState } from "react";

export interface AnimationScene {
  index: number;
  title: string;
  narration: string;
  visuals: string;
  formula: string;
  purpose: string;
  duration: string;
  notes: string;
}

interface AnimationPlayerProps {
  content: string;
  title: string;
}

type SceneDraft = Omit<AnimationScene, "index">;
type SceneField = keyof SceneDraft;

const SCENE_DURATION_MS = 5200;
const CHINESE_NUMERAL = "零一二三四五六七八九十";
const EXPLICIT_SCENE_MARKER = new RegExp(
  String.raw`^(?:#{1,6}\s*)?(?:[-*+]\s*)?(?:\*\*)?\s*(?:第\s*[\d${CHINESE_NUMERAL}]+\s*(?:个)?\s*)?(?:镜头|分镜|场景|片段|Scene)\s*[\d${CHINESE_NUMERAL}]*\s*(?:\*\*)?\s*[：:.\-\s]*(.*)$`,
  "i"
);
const NUMBERED_SCENE_MARKER = new RegExp(
  String.raw`^(?:#{1,6}\s*)?(?:[-*+]\s*)?(?:\*\*)?\s*[\d${CHINESE_NUMERAL}]+\s*[.、]\s*(?:镜头|分镜|场景|片段)\s*[：:.\-\s]*(.*)$`,
  "i"
);

function createEmptyScene(title: string): SceneDraft {
  return {
    title,
    narration: "",
    visuals: "",
    formula: "",
    purpose: "",
    duration: "",
    notes: "",
  };
}

function cleanLine(line: string): string {
  return line
    .replace(/^\s*(?:[-*+>]\s*)+/, "")
    .replace(/^\s*\d+[.、]\s*/, "")
    .replace(/\*\*/g, "")
    .trim();
}

function normalizeWhitespace(value: string): string {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n")
    .trim();
}

function extractSceneTitle(line: string): string | null {
  const cleaned = cleanLine(line.replace(/^#{1,6}\s*/, ""));
  if (!cleaned) return null;
  const explicit = cleaned.match(EXPLICIT_SCENE_MARKER);
  if (explicit) return explicit[1]?.trim() || cleaned;
  const numbered = cleaned.match(NUMBERED_SCENE_MARKER);
  if (numbered) return numbered[1]?.trim() || cleaned;
  return null;
}

function classifyField(line: string): { field: SceneField; value: string } | null {
  const cleaned = cleanLine(line);
  const match = cleaned.match(/^([^：:]{1,12})[：:]\s*(.*)$/);
  if (!match) return null;

  const label = match[1].trim();
  const value = match[2].trim();

  if (/^(旁白|解说|讲解词|台词)$/.test(label)) {
    return { field: "narration", value };
  }
  if (/^(画面|画面元素|视觉|视觉元素|可视化|动画|动作|镜头说明)$/.test(label)) {
    return { field: "visuals", value };
  }
  if (/^(关键公式|公式|代码|关键代码|可视化建议|公式或代码)$/.test(label)) {
    return { field: "formula", value };
  }
  if (/^(学习目的|目的|意图|目标)$/.test(label)) {
    return { field: "purpose", value };
  }
  if (/^(时长|时间|预计时长)$/.test(label)) {
    return { field: "duration", value };
  }

  return null;
}

function appendToField(scene: SceneDraft, field: SceneField, value: string) {
  if (!value) return;
  scene[field] = scene[field] ? `${scene[field]}\n${value}` : value;
}

function finalizeScene(scene: SceneDraft, index: number): AnimationScene {
  return {
    index,
    title: normalizeWhitespace(scene.title) || `镜头 ${index + 1}`,
    narration: normalizeWhitespace(scene.narration),
    visuals: normalizeWhitespace(scene.visuals),
    formula: normalizeWhitespace(scene.formula),
    purpose: normalizeWhitespace(scene.purpose),
    duration: normalizeWhitespace(scene.duration),
    notes: normalizeWhitespace(scene.notes),
  };
}

function splitFallbackScenes(content: string): AnimationScene[] {
  const paragraphs = content
    .replace(/^#{1,2}\s+.*$/m, "")
    .split(/\n{2,}/)
    .map((item) => normalizeWhitespace(item))
    .filter(Boolean);

  const source = paragraphs.length > 0 ? paragraphs : [normalizeWhitespace(content)];
  if (source.length === 0 || !source[0]) return [];

  const targetCount = Math.min(6, Math.max(1, source.length));
  const bucketSize = Math.ceil(source.length / targetCount);

  return Array.from({ length: targetCount }, (_, i) => {
    const body = source.slice(i * bucketSize, (i + 1) * bucketSize).join("\n\n");
    return finalizeScene(
      {
        ...createEmptyScene(`片段 ${i + 1}`),
        narration: body,
        visuals: body,
      },
      i
    );
  }).filter((scene) => scene.narration || scene.visuals);
}

export function parseAnimationScript(content: string): AnimationScene[] {
  const normalizedContent = content.replace(/\r\n/g, "\n").trim();
  if (!normalizedContent) return [];

  const lines = normalizedContent.split("\n");
  const scenes: SceneDraft[] = [];
  let current: SceneDraft | null = null;
  let currentField: SceneField | null = null;

  for (const line of lines) {
    const sceneTitle = extractSceneTitle(line);
    if (sceneTitle) {
      current = createEmptyScene(sceneTitle);
      scenes.push(current);
      currentField = null;
      continue;
    }

    if (!current) continue;

    const field = classifyField(line);
    if (field) {
      currentField = field.field;
      appendToField(current, field.field, field.value);
      continue;
    }

    const cleaned = cleanLine(line);
    if (!cleaned) {
      currentField = null;
      continue;
    }

    appendToField(current, currentField ?? "notes", cleaned);
  }

  const parsed = scenes
    .map((scene, index) => finalizeScene(scene, index))
    .filter((scene) => scene.title || scene.narration || scene.visuals || scene.notes);

  return parsed.length > 0 ? parsed : splitFallbackScenes(normalizedContent);
}

function splitVisualCues(scene: AnimationScene): string[] {
  const source = scene.visuals || scene.formula || scene.notes || scene.narration || scene.title;
  return source
    .replace(/[；;]/g, "\n")
    .replace(/[，,、]/g, "\n")
    .split("\n")
    .map((item) => item.replace(/^[-*+]\s*/, "").trim())
    .filter(Boolean)
    .slice(0, 5);
}

function fieldOrFallback(value: string, fallback: string): string {
  return value.trim() || fallback;
}

export function AnimationPlayer({ content, title }: AnimationPlayerProps) {
  const scenes = useMemo(() => parseAnimationScript(content), [content]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [sceneProgress, setSceneProgress] = useState(0);

  const safeCurrentIndex = Math.min(currentIndex, Math.max(0, scenes.length - 1));

  useEffect(() => {
    if (!isPlaying || scenes.length <= 1) return;

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      const progress = ((Date.now() - startedAt) / SCENE_DURATION_MS) * 100;
      if (progress >= 100) {
        setSceneProgress(0);
        setCurrentIndex((index) => (Math.min(index, scenes.length - 1) + 1) % scenes.length);
        return;
      }
      setSceneProgress(progress);
    }, 120);

    return () => window.clearInterval(timer);
  }, [safeCurrentIndex, isPlaying, scenes.length]);

  if (scenes.length === 0) {
    return (
      <div className="rounded-xl bg-[var(--color-warm-gray-50)] p-4 text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
        暂无可展示的动画脚本内容。
      </div>
    );
  }

  const scene = scenes[safeCurrentIndex] ?? scenes[0];
  const visualCues = splitVisualCues(scene);
  const overallProgress = ((safeCurrentIndex + sceneProgress / 100) / scenes.length) * 100;

  function selectScene(index: number) {
    setCurrentIndex(index);
    setSceneProgress(0);
  }

  function goPrevious() {
    selectScene(safeCurrentIndex === 0 ? scenes.length - 1 : safeCurrentIndex - 1);
  }

  function goNext() {
    selectScene((safeCurrentIndex + 1) % scenes.length);
  }

  return (
    <div className="space-y-3">
      <div className="relative aspect-[16/9] overflow-hidden rounded-xl bg-[#2a2820] p-4 text-white shadow-lg ring-1 ring-black/10 sm:p-6">
        <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(250,249,245,.14)_1px,transparent_1px),linear-gradient(90deg,rgba(250,249,245,.14)_1px,transparent_1px)] [background-size:36px_36px]" />
        <div className="absolute left-6 top-6 h-20 w-20 rounded-full bg-[#c96442]/25 blur-2xl" />
        <div className="absolute bottom-8 right-8 h-24 w-24 rounded-full bg-[#6b8e6b]/20 blur-2xl" />

        <div className="relative z-10 flex h-full flex-col justify-between gap-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-[0.18em] text-[#c8c4b8]">
                {title}
              </p>
              <h3 className="mt-2 break-words text-lg font-serif leading-tight text-[#fff8f0] sm:text-2xl">
                {scene.title}
              </h3>
            </div>
            <div className="shrink-0 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-[#e8e0d4]">
              {safeCurrentIndex + 1} / {scenes.length}
            </div>
          </div>

          <div className="grid min-h-0 flex-1 items-center gap-4 sm:grid-cols-[1.1fr_.9fr]">
            <div className="min-h-0">
              <div className="relative mx-auto flex aspect-square max-h-44 max-w-44 items-center justify-center rounded-full border border-[#faf9f5]/15 bg-[#faf9f5]/8 sm:max-h-56 sm:max-w-56">
                <div className="absolute h-[76%] w-[76%] rounded-full border border-dashed border-[#c96442]/60" />
                <div className="absolute h-[48%] w-[48%] rounded-full border border-[#6b8e6b]/50" />
                <div
                  className={`h-16 w-16 rounded-2xl bg-[#c96442] shadow-[0_0_36px_rgba(201,100,66,.45)] transition-transform duration-500 ${
                    isPlaying ? "scale-110 rotate-6" : "scale-100"
                  }`}
                />
                {visualCues.slice(0, 4).map((cue, i) => (
                  <span
                    key={`${cue}-${i}`}
                    className={`absolute h-3 w-3 rounded-full ${
                      i % 2 === 0 ? "bg-[#f0c36d]" : "bg-[#8fb1c8]"
                    } ${isPlaying ? "animate-pulse" : ""}`}
                    style={{
                      left: `${50 + Math.cos((i / 4) * Math.PI * 2) * 38}%`,
                      top: `${50 + Math.sin((i / 4) * Math.PI * 2) * 38}%`,
                    }}
                  />
                ))}
              </div>
            </div>

            <div className="min-h-0 space-y-3 overflow-hidden">
              <p className="line-clamp-4 text-sm leading-7 text-[#e8e0d4]">
                {fieldOrFallback(scene.narration, scene.purpose || scene.notes || scene.visuals)}
              </p>
              <div className="flex flex-wrap gap-2">
                {visualCues.map((cue, i) => (
                  <span
                    key={`${cue}-${i}`}
                    className="max-w-full truncate rounded-full border border-white/15 bg-white/10 px-2.5 py-1 text-xs text-[#f5f4ed]"
                    title={cue}
                  >
                    {cue}
                  </span>
                ))}
              </div>
              {scene.formula && (
                <div className="rounded-lg border border-white/12 bg-black/15 px-3 py-2 text-xs leading-6 text-[#f7e1b1]">
                  {scene.formula}
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="h-1 overflow-hidden rounded-full bg-white/15">
              <div
                className="h-full rounded-full bg-[#c96442] transition-all duration-150"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={goPrevious}
            className="rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)]"
          >
            上一镜
          </button>
          <button
            type="button"
            onClick={() => {
              setSceneProgress(0);
              setIsPlaying((value) => !value);
            }}
            className="rounded-lg bg-[var(--color-terracotta)] px-3 py-1.5 text-xs text-white transition-colors hover:bg-[var(--color-terracotta-hover)]"
          >
            {isPlaying ? "暂停" : "播放"}
          </button>
          <button
            type="button"
            onClick={goNext}
            className="rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)]"
          >
            下一镜
          </button>
        </div>
        {scene.duration && (
          <span className="text-xs text-[var(--color-warm-gray-400)]">
            时长：{scene.duration}
          </span>
        )}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {scenes.map((item, i) => (
          <button
            key={`${item.title}-${i}`}
            type="button"
            onClick={() => selectScene(i)}
            className={`min-w-24 max-w-36 rounded-lg px-3 py-2 text-left text-xs transition-colors ${
              i === safeCurrentIndex
                ? "bg-[var(--color-terracotta)] text-white"
                : "bg-[var(--color-warm-gray-50)] text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] hover:bg-[var(--color-parchment)]"
            }`}
          >
            <span className="block text-[10px] opacity-70">镜头 {i + 1}</span>
            <span className="line-clamp-2 break-words">{item.title}</span>
          </button>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-lg bg-[var(--color-warm-gray-50)] p-3 ring-1 ring-[var(--color-warm-gray-200)]">
          <p className="mb-1 text-xs font-medium text-[var(--color-warm-gray-500)]">旁白</p>
          <p className="whitespace-pre-line text-sm leading-7 text-[var(--color-warm-gray-700)]">
            {fieldOrFallback(scene.narration, scene.notes || "本镜头暂无旁白。")}
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-warm-gray-50)] p-3 ring-1 ring-[var(--color-warm-gray-200)]">
          <p className="mb-1 text-xs font-medium text-[var(--color-warm-gray-500)]">画面</p>
          <p className="whitespace-pre-line text-sm leading-7 text-[var(--color-warm-gray-700)]">
            {fieldOrFallback(scene.visuals, scene.formula || "本镜头暂无画面说明。")}
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-warm-gray-50)] p-3 ring-1 ring-[var(--color-warm-gray-200)]">
          <p className="mb-1 text-xs font-medium text-[var(--color-warm-gray-500)]">学习目的</p>
          <p className="whitespace-pre-line text-sm leading-7 text-[var(--color-warm-gray-700)]">
            {fieldOrFallback(scene.purpose, scene.notes || "本镜头暂无学习目的。")}
          </p>
        </div>
      </div>
    </div>
  );
}
