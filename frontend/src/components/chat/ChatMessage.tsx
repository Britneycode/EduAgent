"use client";

import { Children, useMemo } from "react";
import { MessageCircleQuestion, RefreshCw } from "lucide-react";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  children?: React.ReactNode;
  isLast?: boolean;
  isStreaming?: boolean;
  onRegenerate?: () => void;
  onFollowUp?: (question: string) => void;
}

function generateSuggestions(content: string): string[] {
  const suggestions: string[] = [];
  const lower = content.toLowerCase();
  if (lower.includes("神经网络") || lower.includes("深度学习")) {
    suggestions.push("能举个具体的应用例子吗？");
    suggestions.push("这和传统机器学习有什么区别？");
    suggestions.push("学习这个需要什么数学基础？");
  } else if (lower.includes("python") || lower.includes("代码")) {
    suggestions.push("能写一个更复杂的例子吗？");
    suggestions.push("这个在真实项目中怎么用？");
    suggestions.push("有哪些常见的坑需要注意？");
  } else if (lower.includes("题") || lower.includes("练习")) {
    suggestions.push("能出几道更难的题吗？");
    suggestions.push("帮我总结一下这个知识点");
    suggestions.push("有哪些易混淆的概念？");
  } else {
    suggestions.push("能再详细解释一下吗？");
    suggestions.push("有什么推荐的参考资料？");
    suggestions.push("能帮我出几道题测试一下吗？");
  }
  return suggestions.slice(0, 3);
}

export function ChatMessage({
  role,
  content,
  children,
  isLast,
  isStreaming,
  onRegenerate,
  onFollowUp,
}: ChatMessageProps) {
  const isUser = role === "user";
  const isResourceTurn = !isUser && Children.count(children) > 0;
  const suggestions = useMemo(
    () => (!isUser && isLast && !isStreaming && content ? generateSuggestions(content) : []),
    [isUser, isLast, isStreaming, content]
  );

  if (isUser) {
    return (
      <div className="mb-4 flex justify-end">
        <div className="max-w-[70%] rounded-2xl rounded-br-md bg-[var(--color-sand)] px-4 py-3 text-[var(--color-near-black)] shadow-[var(--shadow-ring)] max-md:max-w-[86%]">
          <div className="whitespace-pre-wrap text-[15px] leading-7 md:text-base">
            {content}
          </div>
        </div>
      </div>
    );
  }

  if (isResourceTurn) {
    return (
      <div className="mb-4 flex justify-start">
        <div className="relative w-full max-w-[840px] pl-5">
          <span className="absolute left-0 top-2 h-[calc(100%-0.5rem)] w-px bg-[var(--color-warm-gray-200)]" />
          <span className="absolute left-[-3px] top-2 h-2 w-2 rounded-full bg-[var(--color-terracotta)]" />
          {content && (
            <div className="mb-2 rounded-xl bg-[var(--color-parchment)]/65 px-3 py-2 text-sm leading-6 text-[var(--color-warm-gray-700)] shadow-[var(--shadow-ring)]">
              <MarkdownRenderer content={content} />
            </div>
          )}
          <div className="space-y-2">{children}</div>

          {suggestions.length > 0 && onFollowUp && (
            <div className="mt-3 border-t border-[var(--color-warm-gray-200)] pt-3">
              <p className="mb-2 inline-flex items-center gap-1.5 text-[11px] text-[var(--color-warm-gray-400)]">
                <MessageCircleQuestion className="h-3.5 w-3.5" />
                继续追问
              </p>
              <div className="flex flex-wrap gap-1.5">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onFollowUp(s)}
                    className="rounded-full bg-[var(--color-parchment)] px-3 py-1 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-terracotta)]/10 hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]/30"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {isLast && !isStreaming && onRegenerate && (
            <div className="mt-3 flex items-center gap-2 border-t border-[var(--color-warm-gray-200)] pt-3">
              <button
                type="button"
                onClick={onRegenerate}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                重新生成
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-5 flex justify-start">
      <div
        className="max-w-[88%] rounded-2xl rounded-bl-md bg-[var(--color-ivory)] px-5 py-4 text-[var(--color-warm-gray-800)] shadow-[var(--shadow-ring)] md:max-w-[78%]"
      >
        <MarkdownRenderer content={content} />

        {/* 追问建议 */}
        {suggestions.length > 0 && onFollowUp && (
          <div className="mt-3 border-t border-[var(--color-warm-gray-200)] pt-3">
            <p className="mb-2 inline-flex items-center gap-1.5 text-[11px] text-[var(--color-warm-gray-400)]">
              <MessageCircleQuestion className="h-3.5 w-3.5" />
              继续追问
            </p>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onFollowUp(s)}
                  className="rounded-full bg-[var(--color-parchment)] px-3 py-1 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-terracotta)]/10 hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]/30"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {!isUser && isLast && !isStreaming && onRegenerate && (
          <div className="mt-3 flex items-center gap-2 border-t border-[var(--color-warm-gray-200)] pt-3">
            <button
              type="button"
              onClick={onRegenerate}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              重新生成
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
