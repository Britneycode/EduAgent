"use client";

import { useThrottledStreamingText } from "@/hooks/useThrottledStreamingText";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

interface StreamingTextProps {
  content: string;
}

export function StreamingText({ content }: StreamingTextProps) {
  // 流式输出时以 40ms（~25fps）节流更新，平衡流畅度与 AST 解析开销
  const throttledContent = useThrottledStreamingText(content, 40);

  if (!throttledContent && !content) {
    return (
      <span className="inline-block h-4 w-2 animate-pulse rounded-sm bg-[var(--color-terracotta)]" />
    );
  }

  return (
    <div className="relative">
      <MarkdownRenderer content={throttledContent || content} />
      <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-[var(--color-terracotta)] align-text-bottom" />
    </div>
  );
}
