import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

interface StreamingTextProps {
  content: string;
}

export function StreamingText({ content }: StreamingTextProps) {
  if (!content) {
    return (
      <span className="inline-block w-2 h-4 bg-[var(--color-terracotta)] animate-pulse rounded-sm" />
    );
  }

  return (
    <div className="relative">
      <MarkdownRenderer content={content} />
      <span className="inline-block w-1.5 h-4 ml-0.5 bg-[var(--color-terracotta)] animate-pulse rounded-sm align-text-bottom" />
    </div>
  );
}
