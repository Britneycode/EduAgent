"use client";

import { useState, useMemo } from "react";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

interface SlideViewerProps {
  content: string;
}

interface Slide {
  title: string;
  body: string;
}

function parseSlides(content: string): Slide[] {
  const pagePattern = /(?:^|\n)#{1,3}\s*第?\s*(\d+)\s*页[：:.]?\s*(.*)/g;
  const matches = [...content.matchAll(pagePattern)];

  if (matches.length >= 2) {
    return matches.map((match, i) => {
      const title = match[2]?.trim() || `第 ${match[1]} 页`;
      const startIdx = match.index! + match[0].length;
      const endIdx = i + 1 < matches.length ? matches[i + 1].index! : content.length;
      const body = content.slice(startIdx, endIdx).trim();
      return { title, body };
    });
  }

  const hrSections = content.split(/\n---+\n/);
  if (hrSections.length >= 3) {
    return hrSections.map((section, i) => {
      const lines = section.trim().split("\n");
      const firstLine = lines[0]?.replace(/^#+\s*/, "").trim() || `第 ${i + 1} 页`;
      const body = lines.slice(1).join("\n").trim();
      return { title: firstLine, body };
    });
  }

  return [];
}

export function SlideViewer({ content }: SlideViewerProps) {
  const slides = useMemo(() => parseSlides(content), [content]);
  const [currentIndex, setCurrentIndex] = useState(0);

  if (slides.length === 0) {
    return <MarkdownRenderer content={content} />;
  }

  const slide = slides[currentIndex];
  const progress = ((currentIndex + 1) / slides.length) * 100;

  return (
    <div>
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-[#3d3529] to-[#2a241c] p-6 text-white shadow-lg aspect-[16/9] flex flex-col">
        <div className="mb-4 text-center">
          <h2 className="text-lg font-serif font-medium leading-tight sm:text-xl">
            {slide.title}
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto text-sm leading-7 text-[#e8e0d4] [&_strong]:text-white [&_li]:mb-1">
          <MarkdownRenderer content={slide.body} className="slide-content" />
        </div>
        <div className="mt-4 flex items-center justify-between text-xs text-[#9a8e7f]">
          <span>EduAgent 教学演示</span>
          <span>{currentIndex + 1} / {slides.length}</span>
        </div>
      </div>

      <div className="mt-2 h-1 overflow-hidden rounded-full bg-[var(--color-warm-gray-200)]">
        <div
          className="h-full rounded-full bg-[var(--color-terracotta)] transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
          disabled={currentIndex === 0}
          className="rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)] disabled:opacity-40 disabled:hover:bg-transparent"
        >
          上一页
        </button>
        <div className="flex gap-1.5">
          {slides.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setCurrentIndex(i)}
              className={`h-2 w-2 rounded-full transition-colors ${
                i === currentIndex
                  ? "bg-[var(--color-terracotta)]"
                  : "bg-[var(--color-warm-gray-200)] hover:bg-[var(--color-warm-gray-300)]"
              }`}
            />
          ))}
        </div>
        <button
          type="button"
          onClick={() => setCurrentIndex((i) => Math.min(slides.length - 1, i + 1))}
          disabled={currentIndex === slides.length - 1}
          className="rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)] disabled:opacity-40 disabled:hover:bg-transparent"
        >
          下一页
        </button>
      </div>
    </div>
  );
}
