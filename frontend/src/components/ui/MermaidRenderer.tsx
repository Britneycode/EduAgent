"use client";

import { useEffect, useRef, useState, useId } from "react";

interface MermaidRendererProps {
  code: string;
}

export function MermaidRenderer({ code }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const uniqueId = useId().replace(/:/g, "-");
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          themeVariables: {
            primaryColor: "#faf9f5",
            primaryBorderColor: "#c96442",
            primaryTextColor: "#3d3529",
            lineColor: "#9a8e7f",
            secondaryColor: "#f5f4ed",
            tertiaryColor: "#fff8f0",
            fontFamily: "Georgia, serif",
          },
        });
        const { svg: rendered } = await mermaid.render(
          `mermaid-${uniqueId}`,
          code.trim()
        );
        if (!cancelled) {
          setSvg(rendered);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setError("思维导图渲染失败，显示源码");
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [code, uniqueId]);

  if (error) {
    return (
      <div>
        <p className="mb-2 text-xs text-[var(--color-warm-gray-400)]">{error}</p>
        <pre className="overflow-x-auto rounded-lg bg-[var(--color-warm-gray-50)] p-3 text-[13px] ring-1 ring-[var(--color-warm-gray-200)]">
          <code>{code}</code>
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-[var(--color-warm-gray-400)]">
        正在渲染思维导图...
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="overflow-x-auto [&_svg]:mx-auto [&_svg]:max-w-full"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
