"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Award,
  BookOpenText,
  CheckCircle2,
  ClipboardList,
  FileText,
  Lightbulb,
  MessageCircleQuestion,
  Trophy,
  XCircle,
} from "lucide-react";
import { submitQuiz } from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type { QuizSubmitResponse } from "@/lib/types";

type QuizQuestionType = "choice" | "judge" | "short_answer";

interface QuizQuestion {
  id: number;
  type: QuizQuestionType;
  question: string;
  options: string[];
  answer: string;
  explanation: string;
  difficulty?: string;
  knowledge_point?: string;
  chapter?: string;
}

interface QuizSettings {
  question_count?: number;
  question_types?: QuizQuestionType[];
  difficulty?: string;
  time_limit_sec?: number;
  chapter_mix?: boolean;
}

interface QuizPayload {
  settings?: QuizSettings;
  questions: QuizQuestion[];
}

interface DiscussionMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface InteractiveQuizProps {
  content: string;
  resourceId?: number | null;
  sessionId?: number | null;
}

const QUESTION_TYPE_LABELS: Record<QuizQuestionType, string> = {
  choice: "选择题",
  judge: "判断题",
  short_answer: "简答题",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "基础",
  medium: "进阶",
  hard: "挑战",
};

function parseQuizContent(content: string): QuizPayload | null {
  try {
    const parsed = JSON.parse(content);
    if (parsed?.questions && Array.isArray(parsed.questions)) {
      return {
        settings: parsed.settings || undefined,
        questions: parsed.questions,
      };
    }
  } catch {
    // 不是 JSON 格式
  }
  return null;
}

function questionTypeLabel(type: string): string {
  return QUESTION_TYPE_LABELS[type as QuizQuestionType] || type;
}

function difficultyLabel(value: string): string {
  return DIFFICULTY_LABELS[value] || value;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function uniqueValues<T extends string>(values: T[]): T[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function interleaveByChapter(questions: QuizQuestion[]): QuizQuestion[] {
  const buckets = new Map<string, QuizQuestion[]>();
  for (const question of questions) {
    const chapter = question.chapter || "default";
    buckets.set(chapter, [...(buckets.get(chapter) || []), question]);
  }

  const ordered: QuizQuestion[] = [];
  while ([...buckets.values()].some((bucket) => bucket.length > 0)) {
    for (const [chapter, bucket] of buckets) {
      const next = bucket.shift();
      if (next) ordered.push(next);
      if (bucket.length === 0) buckets.delete(chapter);
    }
  }
  return ordered;
}

function buildWeakPoints(
  questions: QuizQuestion[],
  answers: Record<number, string>,
  revealed: Record<number, boolean>
): string[] {
  const weak = questions
    .filter((q) => q.options.length > 0 && revealed[q.id] && answers[q.id] !== q.answer)
    .map((q) => q.knowledge_point || q.chapter || "未标注知识点");
  return uniqueValues(weak);
}

function buildAccuracyByType(
  questions: QuizQuestion[],
  answers: Record<number, string>,
  revealed: Record<number, boolean>
): Record<string, number> {
  const totals: Record<string, { correct: number; total: number }> = {};
  for (const question of questions) {
    if (!revealed[question.id] || question.options.length === 0) continue;
    const bucket = totals[question.type] || { correct: 0, total: 0 };
    bucket.total += 1;
    if (answers[question.id] === question.answer) bucket.correct += 1;
    totals[question.type] = bucket;
  }
  return Object.fromEntries(
    Object.entries(totals).map(([type, bucket]) => [
      type,
      bucket.total > 0 ? Math.round((bucket.correct / bucket.total) * 100) : 0,
    ])
  );
}

/** 根据题目内容生成一段简短的总结 */
function generateSummary(q: QuizQuestion, isCorrect: boolean): string {
  if (isCorrect) {
    return `你答对了！${q.knowledge_point ? `这道题考察的是「${q.knowledge_point}」` : ""}你已经掌握了这个知识点，继续保持！`;
  }
  return `这道题的正确答案是 ${q.answer}。${q.knowledge_point ? `核心考点是「${q.knowledge_point}」` : ""}建议重点复习相关内容。`;
}

export function InteractiveQuiz({ content, resourceId, sessionId }: InteractiveQuizProps) {
  const quiz = useMemo(() => parseQuizContent(content), [content]);
  const questions = useMemo(() => quiz?.questions || [], [quiz]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});
  const [examMode, setExamMode] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverReport, setServerReport] = useState<QuizSubmitResponse | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<QuizQuestionType[]>([]);
  const [selectedDifficulty, setSelectedDifficulty] = useState("all");
  const [questionLimit, setQuestionLimit] = useState(10);
  const [timedMode, setTimedMode] = useState(true);
  const [timeLimitSec, setTimeLimitSec] = useState(600);
  const [chapterMix, setChapterMix] = useState(true);
  const [started, setStarted] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const [finishedAt, setFinishedAt] = useState<number | null>(null);
  const [clockNow, setClockNow] = useState(Date.now());
  const startTime = useRef(Date.now());

  // ---- 逐题模式状态 ----
  const [currentIndex, setCurrentIndex] = useState(0);
  // 每道题的 AI 讨论消息
  const [discussions, setDiscussions] = useState<Record<number, DiscussionMessage[]>>({});
  const [discussionInput, setDiscussionInput] = useState("");
  const [discussing, setDiscussing] = useState(false);
  const [discussionStreaming, setDiscussionStreaming] = useState("");
  const discussionAbortRef = useRef<AbortController | null>(null);

  const availableTypes = useMemo(
    () => uniqueValues(questions.map((q) => q.type)),
    [questions]
  );
  const availableDifficulties = useMemo(
    () => uniqueValues(questions.map((q) => q.difficulty || "").filter(Boolean)),
    [questions]
  );

  useEffect(() => {
    if (!quiz) return;
    const defaultTypes = quiz.settings?.question_types?.length
      ? quiz.settings.question_types
      : availableTypes;
    setSelectedTypes(defaultTypes);
    setSelectedDifficulty(quiz.settings?.difficulty || "all");
    setQuestionLimit(
      Math.min(quiz.settings?.question_count || 10, Math.max(questions.length, 1))
    );
    setTimedMode(quiz.settings?.time_limit_sec !== 0);
    setTimeLimitSec(quiz.settings?.time_limit_sec || 600);
    setChapterMix(quiz.settings?.chapter_mix ?? true);
    // 重置所有状态
    setStarted(false);
    setTimedOut(false);
    setFinishedAt(null);
    setServerReport(null);
    setAnswers({});
    setRevealed({});
    setSubmitted(false);
    setCurrentIndex(0);
    setDiscussions({});
    setDiscussionInput("");
    setDiscussing(false);
    setDiscussionStreaming("");
  }, [availableTypes, questions.length, quiz]);

  const filteredQuestions = useMemo(() => {
    const byType = questions.filter(
      (question) =>
        selectedTypes.length === 0 || selectedTypes.includes(question.type)
    );
    const byDifficulty =
      selectedDifficulty === "all"
        ? byType
        : byType.filter((question) => question.difficulty === selectedDifficulty);
    return chapterMix ? interleaveByChapter(byDifficulty) : byDifficulty;
  }, [chapterMix, questions, selectedDifficulty, selectedTypes]);

  const activeQuestions = useMemo(
    () => filteredQuestions.slice(0, Math.max(1, questionLimit)),
    [filteredQuestions, questionLimit]
  );

  const currentQuestion = activeQuestions[currentIndex] || null;
  const isLastQuestion = currentIndex >= activeQuestions.length - 1;

  const handleSubmitToServer = useCallback(
    async (
      finalRevealed: Record<number, boolean>,
      finalAnswers: Record<number, string>,
      finalQuestions: QuizQuestion[]
    ) => {
      if (!resourceId || submitted || submitting) return;
      const allRevealed = finalQuestions.every((q) => finalRevealed[q.id]);
      if (!allRevealed) return;

      setSubmitting(true);
      try {
        const durationSec = Math.round((Date.now() - startTime.current) / 1000);
        const result = await submitQuiz({
          resource_id: resourceId,
          answers: finalQuestions.map((q) => ({
            question_id: q.id,
            user_answer: (finalAnswers[q.id] || "").trim(),
          })),
          duration_sec: durationSec,
        });
        setServerReport(result);
        setSubmitted(true);
      } catch {
        // 提交失败不阻塞本地报告
      } finally {
        setSubmitting(false);
      }
    },
    [resourceId, submitted, submitting]
  );

  useEffect(() => {
    if (!started || !timedMode || finishedAt !== null) return;
    const interval = window.setInterval(() => setClockNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [finishedAt, started, timedMode]);

  const elapsedSec = started
    ? Math.max(0, Math.round(((finishedAt || clockNow) - startTime.current) / 1000))
    : 0;
  const remainingSec = timedMode ? Math.max(0, timeLimitSec - elapsedSec) : null;
  const totalRevealed = activeQuestions.filter((q) => revealed[q.id]).length;
  const isComplete = activeQuestions.length > 0 && totalRevealed === activeQuestions.length;

  useEffect(() => {
    if (!started || !timedMode || timedOut || isComplete || remainingSec !== 0) return;
    const finalRevealed = Object.fromEntries(
      activeQuestions.map((question) => [question.id, true])
    );
    setTimedOut(true);
    setRevealed(finalRevealed);
    setFinishedAt(Date.now());
    void handleSubmitToServer(finalRevealed, answers, activeQuestions);
  }, [
    activeQuestions,
    answers,
    handleSubmitToServer,
    isComplete,
    remainingSec,
    started,
    timedMode,
    timedOut,
  ]);

  if (!quiz) return null;

  const objectiveQuestions = activeQuestions.filter((q) => q.options.length > 0);
  const hasShortAnswer = objectiveQuestions.length < activeQuestions.length;
  const correctCount = objectiveQuestions.filter(
    (q) => revealed[q.id] && answers[q.id] === q.answer
  ).length;
  const weakPoints = serverReport?.weak_points?.length
    ? serverReport.weak_points
    : buildWeakPoints(activeQuestions, answers, revealed);
  const accuracyByType =
    serverReport?.accuracy_by_type ||
    buildAccuracyByType(activeQuestions, answers, revealed);

  // ---- 开始 ----
  const handleStart = () => {
    startTime.current = Date.now();
    setClockNow(Date.now());
    setFinishedAt(null);
    setTimedOut(false);
    setAnswers({});
    setRevealed({});
    setSubmitted(false);
    setServerReport(null);
    setCurrentIndex(0);
    setDiscussions({});
    setStarted(true);
  };

  // ---- 选择选项（选择题/判断题）----
  const handleSelect = (qId: number, option: string) => {
    if (revealed[qId]) return;
    const letter = option.charAt(0);
    const newAnswers = { ...answers, [qId]: letter };
    if (examMode) {
      // 考试模式：记录答案但不立即揭示
      setAnswers(newAnswers);
      return;
    }
    const newRevealed = { ...revealed, [qId]: true };
    setAnswers(newAnswers);
    setRevealed(newRevealed);
    const willComplete = activeQuestions.every((q) => newRevealed[q.id]);
    if (willComplete) setFinishedAt(Date.now());
    void handleSubmitToServer(newRevealed, newAnswers, activeQuestions);
  };

  // 考试模式：交卷
  const handleExamSubmit = () => {
    const allRevealed = Object.fromEntries(
      activeQuestions.map((q) => [q.id, true])
    );
    setRevealed(allRevealed);
    setFinishedAt(Date.now());
    void handleSubmitToServer(allRevealed, answers, activeQuestions);
  };

  // ---- 简答题提交 ----
  const handleShortAnswerSubmit = (qId: number) => {
    if (revealed[qId]) return;
    const userAnswer = (answers[qId] || "").trim();
    if (!userAnswer) return; // 空内容不允许提交
    const newRevealed = { ...revealed, [qId]: true };
    setRevealed(newRevealed);
    const willComplete = activeQuestions.every((q) => newRevealed[q.id]);
    if (willComplete) setFinishedAt(Date.now());
    void handleSubmitToServer(newRevealed, answers, activeQuestions);
  };

  const handleShortAnswer = (qId: number, value: string) => {
    if (revealed[qId]) return;
    setAnswers((prev) => ({ ...prev, [qId]: value }));
  };

  // ---- 下一题 ----
  const handleNext = () => {
    if (isLastQuestion) return;
    setCurrentIndex((prev) => prev + 1);
    setDiscussionInput("");
    setDiscussionStreaming("");
  };

  // ---- 上一题 ----
  const handlePrev = () => {
    if (currentIndex <= 0 || examMode) return;
    setCurrentIndex((prev) => prev - 1);
    setDiscussionInput("");
    setDiscussionStreaming("");
  };

  // ---- AI 讨论 ----
  const handleDiscussionSend = async () => {
    const trimmed = discussionInput.trim();
    if (!trimmed || discussing) return;

    const q = currentQuestion;
    if (!q) return;

    const userMsg: DiscussionMessage = {
      id: `discuss-user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };

    setDiscussions((prev) => ({
      ...prev,
      [q.id]: [...(prev[q.id] || []), userMsg],
    }));
    setDiscussionInput("");
    setDiscussing(true);
    setDiscussionStreaming("");

    const controller = new AbortController();
    discussionAbortRef.current = controller;

    // 构造上下文消息：把当前题目信息和用户问题一起发送
    const contextMessage = `【当前题目】${q.question}
【选项】${q.options.join("；")}
【正确答案】${q.answer}
【解析】${q.explanation}
【我的回答】${answers[q.id] || "未作答"}
【我的问题】${trimmed}

请针对上述题目和我的问题进行解答，帮助我理解相关知识点。回答要简明扼要，用中文。`;

    let collectedContent = "";

    await streamChat(
      sessionId ?? null,
      contextMessage,
      {
        onToken: (payload) => {
          collectedContent += payload.token;
          setDiscussionStreaming(collectedContent);
        },
        onError: (payload) => {
          setDiscussionStreaming(`出错了：${payload.message}`);
        },
        onDone: () => {
          if (collectedContent) {
            const assistantMsg: DiscussionMessage = {
              id: `discuss-assistant-${Date.now()}`,
              role: "assistant",
              content: collectedContent,
            };
            setDiscussions((prev) => ({
              ...prev,
              [q.id]: [...(prev[q.id] || []), assistantMsg],
            }));
          }
          setDiscussionStreaming("");
          setDiscussing(false);
        },
      },
      controller.signal,
      { studyMode: true }
    );
  };

  const handleDiscussionKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleDiscussionSend();
    }
  };

  const toggleQuestionType = (type: QuizQuestionType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type]
    );
  };

  // ==================== 设置界面 ====================
  if (!started) {
    const maxQuestionCount = Math.max(filteredQuestions.length, 1);
    return (
      <div className="space-y-3">
        <div className="border-l-2 border-[var(--color-warm-gray-300)] bg-[var(--color-parchment)]/70 px-3 py-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs font-medium text-[var(--color-warm-gray-800)]">
                训练设置
              </p>
              <p className="text-[11px] text-[var(--color-warm-gray-500)]">
                共 {filteredQuestions.length} 题可用 · 本次 {Math.min(questionLimit, filteredQuestions.length)} 题
              </p>
            </div>
            <button
              type="button"
              onClick={handleStart}
              disabled={filteredQuestions.length === 0}
              className="rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              开始练习
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <p className="mb-1 text-[11px] text-[var(--color-warm-gray-500)]">题型</p>
              <div className="flex flex-wrap gap-2">
                {availableTypes.map((type) => (
                  <label
                    key={type}
                    className="flex items-center gap-1.5 text-xs text-[var(--color-warm-gray-600)]"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(type)}
                      onChange={() => toggleQuestionType(type)}
                      className="h-3.5 w-3.5 accent-[var(--color-terracotta)]"
                    />
                    {questionTypeLabel(type)}
                  </label>
                ))}
              </div>
            </div>

            <label className="text-xs text-[var(--color-warm-gray-600)]">
              <span className="mb-1 block text-[11px] text-[var(--color-warm-gray-500)]">难度</span>
              <select
                value={selectedDifficulty}
                onChange={(event) => setSelectedDifficulty(event.target.value)}
                className="w-full rounded-lg bg-[var(--color-ivory)] px-3 py-2 text-xs ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)]"
              >
                <option value="all">全部</option>
                {availableDifficulties.map((difficulty) => (
                  <option key={difficulty} value={difficulty}>
                    {difficultyLabel(difficulty)}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs text-[var(--color-warm-gray-600)]">
              <span className="mb-1 block text-[11px] text-[var(--color-warm-gray-500)]">题量</span>
              <input
                type="number"
                min={1}
                max={maxQuestionCount}
                value={Math.min(questionLimit, maxQuestionCount)}
                onChange={(event) =>
                  setQuestionLimit(
                    Math.min(Math.max(Number(event.target.value) || 1, 1), maxQuestionCount)
                  )
                }
                className="w-full rounded-lg bg-[var(--color-ivory)] px-3 py-2 text-xs ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)]"
              />
            </label>

            <label className="text-xs text-[var(--color-warm-gray-600)]">
              <span className="mb-1 block text-[11px] text-[var(--color-warm-gray-500)]">限时（分钟）</span>
              <input
                type="number"
                min={1}
                max={120}
                value={Math.max(1, Math.round(timeLimitSec / 60))}
                onChange={(event) =>
                  setTimeLimitSec(Math.max(Number(event.target.value) || 1, 1) * 60)
                }
                disabled={!timedMode}
                className="w-full rounded-lg bg-[var(--color-ivory)] px-3 py-2 text-xs ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)] disabled:opacity-50"
              />
            </label>
          </div>

          <div className="mt-3 flex flex-wrap gap-4">
            <label className="flex items-center gap-1.5 text-xs text-[var(--color-warm-gray-600)]">
              <input
                type="checkbox"
                checked={timedMode}
                onChange={(event) => setTimedMode(event.target.checked)}
                className="h-3.5 w-3.5 accent-[var(--color-terracotta)]"
              />
              限时训练
            </label>
            <label className="flex items-center gap-1.5 text-xs text-[var(--color-warm-gray-600)]">
              <input
                type="checkbox"
                checked={chapterMix}
                onChange={(event) => setChapterMix(event.target.checked)}
                className="h-3.5 w-3.5 accent-[var(--color-terracotta)]"
              />
              章节混合
            </label>
            <label className="flex items-center gap-1.5 text-xs text-[var(--color-warm-gray-600)]">
              <input
                type="checkbox"
                checked={examMode}
                onChange={(event) => setExamMode(event.target.checked)}
                className="h-3.5 w-3.5 accent-[var(--color-terracotta)]"
              />
              <Trophy className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
              考试模式（全部答完才出分）
            </label>
          </div>
        </div>
      </div>
    );
  }

  // ==================== 完成总结界面 ====================
  if (isComplete) {
    return (
      <div className="space-y-4">
        {/* 状态栏 */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-l-2 border-[var(--color-warm-gray-300)] bg-[var(--color-parchment)]/70 px-3 py-2 text-xs text-[var(--color-warm-gray-600)]">
          <span>{activeQuestions.length} 题 · 全部完成</span>
          <span>用时 {formatDuration(elapsedSec)}</span>
        </div>

        {/* 成绩总结 */}
        <div className="rounded-xl bg-[var(--color-parchment)] px-4 py-4 ring-1 ring-[var(--color-warm-gray-200)]">
          <div className="text-center">
            <Award className="mx-auto mb-2 h-10 w-10 text-[var(--color-terracotta)]" />
            <p className="mb-1 text-lg font-medium text-[var(--color-warm-gray-800)]">
              {timedOut ? "时间到！练习结束" : "练习完成！"}
            </p>
            <p className="mb-4 text-sm text-[var(--color-warm-gray-500)]">
              {hasShortAnswer && objectiveQuestions.length === 0
                ? "简答题已提交"
                : hasShortAnswer
                  ? `客观题正确 ${correctCount}/${objectiveQuestions.length} 题`
                  : `正确 ${correctCount}/${activeQuestions.length} 题`}
              {serverReport && (
                <span className="ml-1 font-medium text-[var(--color-terracotta)]">
                  （得分 {serverReport.score}）
                </span>
              )}
            </p>

            {/* 各题型正确率 */}
            <div className="mb-4 flex flex-wrap justify-center gap-2">
              {Object.entries(accuracyByType).map(([type, accuracy]) => (
                <span
                  key={type}
                  className={`rounded-full px-3 py-1 text-xs ${
                    accuracy >= 80
                      ? "bg-green-50 text-green-700"
                      : accuracy >= 60
                        ? "bg-yellow-50 text-yellow-700"
                        : "bg-red-50 text-red-700"
                  }`}
                >
                  {questionTypeLabel(type)}：{accuracy}%
                </span>
              ))}
            </div>

            {/* 薄弱点 */}
            {weakPoints.length > 0 && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-left text-xs">
                <p className="mb-1 font-medium text-red-700">需要加强的知识点：</p>
                <p className="text-red-600">{weakPoints.join("、")}</p>
              </div>
            )}

            {submitting && (
              <p className="mt-3 text-xs text-[var(--color-warm-gray-400)]">正在同步到学习档案...</p>
            )}
            {submitted && (
              <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-[var(--color-warm-gray-400)]">
                已记录到学习档案
                <CheckCircle2 className="h-3.5 w-3.5 text-[var(--color-resource-mindmap)]" />
              </p>
            )}
          </div>
        </div>

        {/* 每道题的回顾 */}
        <div className="space-y-3">
          <p className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-warm-gray-700)]">
            <ClipboardList className="h-4 w-4 text-[var(--color-terracotta)]" />
            答题回顾
          </p>
          {activeQuestions.map((q) => {
            const userAnswer = answers[q.id];
            const isCorrect = q.options.length > 0 && userAnswer === q.answer;
            return (
              <div
                key={q.id}
                className="rounded-xl bg-[var(--color-parchment)] p-3 ring-1 ring-[var(--color-warm-gray-200)]"
              >
                <div className="flex items-start gap-2">
                  <span
                    className={`mt-0.5 shrink-0 text-sm ${isCorrect ? "" : "font-medium text-red-600"}`}
                  >
                    {q.options.length > 0
                      ? isCorrect
                        ? <CheckCircle2 className="h-4 w-4 text-green-600" />
                        : <XCircle className="h-4 w-4 text-red-600" />
                      : <FileText className="h-4 w-4 text-[var(--color-terracotta)]" />}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--color-warm-gray-800)]">{q.question}</p>
                    {q.options.length > 0 && (
                      <p className="mt-1 text-xs text-[var(--color-warm-gray-500)]">
                        你的答案：{userAnswer || "未作答"} · 正确答案：{q.answer}
                      </p>
                    )}
                    {!q.options.length && (
                      <p className="mt-1 text-xs text-[var(--color-warm-gray-500)]">
                        参考答案：{q.answer}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 重新开始 */}
        <div className="text-center">
          <button
            type="button"
            onClick={handleStart}
            className="rounded-lg bg-[var(--color-terracotta)] px-5 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)]"
          >
            再来一组
          </button>
        </div>
      </div>
    );
  }

  // ==================== 逐题练习界面 ====================
  if (!currentQuestion) {
    return null;
  }

  const q = currentQuestion;
  const userAnswer = answers[q.id];
  const isRevealed = revealed[q.id];
  const isObjective = q.options.length > 0;
  const isCorrect = isObjective && userAnswer === q.answer;
  const hasAnswer = isObjective ? Boolean(userAnswer) : Boolean(userAnswer?.trim());
  const currentDiscussions = discussions[q.id] || [];
  const summary = isRevealed ? generateSummary(q, isCorrect) : "";

  return (
    <div className="space-y-4">
      {/* 顶部状态栏 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--color-parchment)]/80 px-3 py-2 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)]">
        <div className="flex items-center gap-3">
          <span className="font-medium text-[var(--color-warm-gray-800)]">
            第 {currentIndex + 1}/{activeQuestions.length} 题
          </span>
          {/* 进度条 */}
          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[var(--color-warm-gray-200)]">
            <div
              className="h-full rounded-full bg-[var(--color-terracotta)] transition-all duration-300"
              style={{ width: `${((currentIndex + 1) / activeQuestions.length) * 100}%` }}
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span>已答 {totalRevealed}/{activeQuestions.length}</span>
          <span>用时 {formatDuration(elapsedSec)}</span>
          {remainingSec !== null && (
            <span className={remainingSec < 60 ? "text-red-500 font-medium" : ""}>
              剩余 {formatDuration(remainingSec)}
            </span>
          )}
        </div>
      </div>

      {/* 题目卡片 */}
      <div className="rounded-xl bg-[var(--color-parchment)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
        {/* 标签 */}
        <div className="mb-4 flex items-center gap-2">
          <span className="shrink-0 rounded-full bg-[var(--color-warm-gray-300)] px-2.5 py-0.5 text-[11px] text-white">
            {questionTypeLabel(q.type)}
          </span>
          {q.difficulty && (
            <span className="shrink-0 rounded-full bg-[var(--color-ivory)] px-2.5 py-0.5 text-[11px] text-[var(--color-warm-gray-500)]">
              {difficultyLabel(q.difficulty)}
            </span>
          )}
          {q.knowledge_point && (
            <span className="shrink-0 truncate rounded-full bg-[var(--color-ivory)] px-2.5 py-0.5 text-[11px] text-[var(--color-warm-gray-400)]">
              {q.knowledge_point}
            </span>
          )}
        </div>

        {/* 题目内容 */}
        <p className="mb-5 text-base leading-7 text-[var(--color-warm-gray-800)]">
          {q.question}
        </p>

        {/* 选项（选择题/判断题） */}
        {q.options.length > 0 && (
          <div className="mb-4 space-y-2.5">
            {q.options.map((opt) => {
              const letter = opt.charAt(0);
              const isSelected = userAnswer === letter;
              const isCorrectOption = q.answer === letter;

              let optionClass =
                "w-full rounded-xl px-4 py-3 text-left text-sm transition-all duration-200 ring-1 ";

              if (isRevealed) {
                if (isCorrectOption) {
                  optionClass += "bg-green-50 text-green-800 ring-green-300 border border-green-300";
                } else if (isSelected && !isCorrectOption) {
                  optionClass += "bg-red-50 text-red-800 ring-red-300 border border-red-300";
                } else {
                  optionClass +=
                    "bg-[var(--color-ivory)] text-[var(--color-warm-gray-400)] ring-[var(--color-warm-gray-200)]";
                }
              } else if (isSelected) {
                optionClass +=
                  "bg-[var(--color-terracotta)]/10 text-[var(--color-terracotta)] ring-[var(--color-terracotta)] border border-[var(--color-terracotta)]";
              } else {
                optionClass +=
                  "bg-[var(--color-ivory)] text-[var(--color-warm-gray-700)] ring-[var(--color-warm-gray-200)] hover:ring-[var(--color-terracotta)] hover:bg-[var(--color-terracotta)]/5 cursor-pointer";
              }

              return (
                <button
                  key={opt}
                  type="button"
                  onClick={() => handleSelect(q.id, opt)}
                  disabled={isRevealed}
                  className={optionClass}
                >
                  <span className="font-medium">{opt.charAt(0)}.</span>
                  <span className="ml-2">{opt.slice(2).trim() || opt}</span>
                  {isRevealed && isCorrectOption && (
                    <span className="ml-2 text-green-600">✓ 正确答案</span>
                  )}
                  {isRevealed && isSelected && !isCorrectOption && (
                    <span className="ml-2 text-red-500">✗ 你的选择</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* 简答题文本区 */}
        {!isObjective && (
          <div className="mb-4 space-y-3">
            <textarea
              value={userAnswer || ""}
              onChange={(event) => handleShortAnswer(q.id, event.target.value)}
              disabled={isRevealed}
              rows={4}
              placeholder="在此输入你的回答..."
              className="w-full resize-y rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-sm leading-6 text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)] disabled:opacity-70"
            />
            {!isRevealed && (
              <button
                type="button"
                onClick={() => handleShortAnswerSubmit(q.id)}
                disabled={!hasAnswer}
                className="rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                提交答案
              </button>
            )}
          </div>
        )}

        {/* 作答反馈 */}
        {isRevealed && (
          <div
            className={`rounded-xl p-4 ${
              isObjective && !isCorrect
                ? "bg-red-50 ring-1 ring-red-200"
                : isObjective && isCorrect
                  ? "bg-green-50 ring-1 ring-green-200"
                  : "bg-blue-50 ring-1 ring-blue-200"
            }`}
          >
            {/* 结果标题 */}
            <div className="mb-2 flex items-center gap-2">
              <span className="text-lg">
                {isObjective
                  ? isCorrect
                    ? <CheckCircle2 className="h-5 w-5 text-green-600" />
                    : <XCircle className="h-5 w-5 text-red-600" />
                  : <FileText className="h-5 w-5 text-[var(--color-terracotta)]" />}
              </span>
              <p className="text-sm font-medium text-[var(--color-warm-gray-800)]">
                {isObjective
                  ? isCorrect
                    ? "回答正确！"
                    : `回答错误，正确答案是 ${q.answer}`
                  : "已提交，请查看参考答案"}
              </p>
            </div>

            {/* 总结/解析 */}
            <p className="mb-1 text-xs text-[var(--color-warm-gray-500)]">{summary}</p>

            {/* 详细解析 */}
            {q.explanation && (
              <div className="mt-3 rounded-lg bg-white/60 px-3 py-2">
                <p className="mb-1 text-xs font-medium text-[var(--color-warm-gray-700)]">
                  <span className="inline-flex items-center gap-1.5">
                    {isObjective && !isCorrect ? (
                      <BookOpenText className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
                    ) : (
                      <Lightbulb className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
                    )}
                    {isObjective && !isCorrect ? "详细解析" : "知识点总结"}
                  </span>
                </p>
                <p className="text-xs leading-5 text-[var(--color-warm-gray-600)]">
                  {q.explanation}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* AI 讨论面板 */}
      {isRevealed && (
        <div className="rounded-xl bg-[var(--color-ivory)] ring-1 ring-[var(--color-warm-gray-200)] overflow-hidden">
          <div className="border-b border-[var(--color-warm-gray-200)] bg-[var(--color-parchment)]/70 px-4 py-2.5">
            <p className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-warm-gray-700)]">
              <MessageCircleQuestion className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
              对这道题有疑问？和 AI 讨论
            </p>
          </div>

          {/* 讨论消息列表 */}
          {currentDiscussions.length > 0 && (
            <div className="max-h-60 overflow-y-auto px-4 py-3 space-y-3">
              {currentDiscussions.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-5 ${
                      msg.role === "user"
                        ? "bg-[var(--color-terracotta)] text-white rounded-br-sm"
                        : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-700)] rounded-bl-sm ring-1 ring-[var(--color-warm-gray-200)]"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 流式响应中 */}
          {discussionStreaming && (
            <div className="px-4 py-3">
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-xl rounded-bl-sm bg-[var(--color-parchment)] px-3 py-2 text-xs leading-5 text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)]">
                  {discussionStreaming}
                  <span className="ml-0.5 inline-block h-3.5 w-1 animate-pulse bg-[var(--color-terracotta)] align-text-bottom" />
                </div>
              </div>
            </div>
          )}

          {/* 输入框 */}
          <div className="border-t border-[var(--color-warm-gray-200)] px-4 py-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={discussionInput}
                onChange={(e) => setDiscussionInput(e.target.value)}
                onKeyDown={handleDiscussionKeyDown}
                placeholder="比如：为什么选这个？能再解释一下吗？"
                disabled={discussing}
                className="flex-1 rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-xs ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)] disabled:opacity-60"
              />
              <button
                type="button"
                onClick={handleDiscussionSend}
                disabled={!discussionInput.trim() || discussing}
                className="shrink-0 rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-xs text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {discussing ? "思考中..." : "发送"}
              </button>
            </div>
            <p className="mt-1.5 text-[10px] text-[var(--color-warm-gray-400)]">
              AI 会根据当前题目内容为你解答疑惑，帮助你深入理解知识点。
            </p>
          </div>
        </div>
      )}

      {/* 导航按钮 */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handlePrev}
          disabled={currentIndex === 0 || examMode}
          className="rounded-lg px-4 py-2 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          ← 上一题
        </button>

        <span className="text-xs text-[var(--color-warm-gray-400)]">
          {currentIndex + 1} / {activeQuestions.length}
        </span>

        {isLastQuestion ? (
          examMode && !isRevealed ? (
            <button
              type="button"
              onClick={handleExamSubmit}
              disabled={!hasAnswer}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-terracotta)] px-6 py-2 text-xs font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trophy className="h-3.5 w-3.5" />
              交卷
            </button>
          ) : (
            <span className="rounded-lg bg-[var(--color-terracotta)]/10 px-4 py-2 text-xs text-[var(--color-terracotta)]">
              已是最后一题
            </span>
          )
        ) : (
          <button
            type="button"
            onClick={handleNext}
            disabled={examMode ? !hasAnswer : !isRevealed}
            className="rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-xs text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            下一题 →
          </button>
        )}
      </div>

      {/* 提示：如果是最后一题且已答完 */}
      {isLastQuestion && isRevealed && (
        <div className="rounded-lg bg-[var(--color-parchment)]/70 px-3 py-2 text-center text-xs text-[var(--color-warm-gray-500)]">
          所有题目已完成，滚动到顶部查看成绩总结 ↑
        </div>
      )}
    </div>
  );
}
