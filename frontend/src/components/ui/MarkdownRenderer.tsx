"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={`markdown-body ${className ?? ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-3 mt-5 text-xl font-medium text-[var(--color-warm-gray-800)] font-serif first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-4 text-lg font-medium text-[var(--color-warm-gray-800)] font-serif first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-3 text-base font-medium text-[var(--color-warm-gray-700)] font-serif first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="mb-2 text-sm leading-7 text-[var(--color-warm-gray-700)] last:mb-0">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="mb-2 ml-4 list-disc space-y-1 text-sm leading-7 text-[var(--color-warm-gray-700)]">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 ml-4 list-decimal space-y-1 text-sm leading-7 text-[var(--color-warm-gray-700)]">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-7">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-[var(--color-warm-gray-800)]">
              {children}
            </strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-3 border-[var(--color-terracotta)]/40 pl-3 text-sm italic text-[var(--color-warm-gray-500)]">
              {children}
            </blockquote>
          ),
          code: ({ className: codeClassName, children, ...props }) => {
            const isBlock = codeClassName?.startsWith("language-") || codeClassName?.startsWith("hljs");
            if (isBlock) {
              return (
                <code className={`${codeClassName ?? ""} text-[13px]`} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded bg-[var(--color-warm-gray-100)] px-1.5 py-0.5 text-[13px] text-[var(--color-terracotta)]">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="my-2 overflow-x-auto rounded-lg bg-[var(--color-warm-gray-50)] p-3 text-[13px] ring-1 ring-[var(--color-warm-gray-200)]">
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto">
              <table className="w-full text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="border-b border-[var(--color-warm-gray-200)] text-left text-xs text-[var(--color-warm-gray-500)]">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 font-medium">{children}</th>
          ),
          td: ({ children }) => (
            <td className="border-b border-[var(--color-warm-gray-100)] px-3 py-2 text-[var(--color-warm-gray-700)]">
              {children}
            </td>
          ),
          hr: () => (
            <hr className="my-4 border-[var(--color-warm-gray-200)]" />
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-terracotta)] underline decoration-[var(--color-terracotta)]/30 hover:decoration-[var(--color-terracotta)]"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
