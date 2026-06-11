"use client";

import { useState } from "react";
import { executeResourceCode } from "@/lib/api";
import type { CodeExecutionResponse, CodeExecutionStatus } from "@/lib/types";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

interface CodeRunnerProps {
  content: string;
  resourceId: number | null;
}

const STATUS_LABELS: Record<CodeExecutionStatus, string> = {
  success: "运行成功",
  error: "运行出错",
  timeout: "执行超时",
  blocked: "安全拦截",
};

const STATUS_CLASSES: Record<CodeExecutionStatus, string> = {
  success: "text-[#4f7d4f]",
  error: "text-[var(--color-terracotta)]",
  timeout: "text-[#9b6b4a]",
  blocked: "text-[var(--color-terracotta)]",
};

export function CodeRunner({ content, resourceId }: CodeRunnerProps) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CodeExecutionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    if (!resourceId || running) return;
    setRunning(true);
    setError(null);
    try {
      const nextResult = await executeResourceCode(resourceId);
      setResult(nextResult);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "运行代码失败");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <MarkdownRenderer content={content} />

      <div className="rounded-xl bg-[var(--color-warm-gray-50)] p-3 ring-1 ring-[var(--color-warm-gray-200)]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-[var(--color-warm-gray-700)]">
              Python 沙箱
            </p>
            {result && (
              <p className={`mt-0.5 text-xs ${STATUS_CLASSES[result.status]}`}>
                {STATUS_LABELS[result.status]} · {result.duration_ms} ms
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={handleRun}
            disabled={!resourceId || running}
            className="rounded-lg bg-[var(--color-terracotta)] px-3 py-1.5 text-xs text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running ? "运行中..." : "运行代码"}
          </button>
        </div>

        {!resourceId && (
          <p className="mt-2 text-xs text-[var(--color-warm-gray-400)]">
            资源保存后可运行代码。
          </p>
        )}

        {error && (
          <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        {result && (result.stdout || result.stderr) && (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {result.stdout && (
              <OutputPanel title="输出" tone="normal" content={result.stdout} />
            )}
            {result.stderr && (
              <OutputPanel title="错误 / 拦截信息" tone="warning" content={result.stderr} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function OutputPanel({
  title,
  tone,
  content,
}: {
  title: string;
  tone: "normal" | "warning";
  content: string;
}) {
  return (
    <div
      className={`rounded-lg p-3 ring-1 ${
        tone === "warning"
          ? "bg-[#fff8f0] ring-[#e6c8b8]"
          : "bg-[var(--color-ivory)] ring-[var(--color-warm-gray-200)]"
      }`}
    >
      <p className="mb-2 text-xs font-medium text-[var(--color-warm-gray-500)]">
        {title}
      </p>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-[var(--color-warm-gray-700)]">
        {content}
      </pre>
    </div>
  );
}
