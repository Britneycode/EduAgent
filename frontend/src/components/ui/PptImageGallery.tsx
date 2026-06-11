"use client";

import { useMemo, useState } from "react";

interface PptSlide {
  title: string;
  key_points: string[];
  summary: string;
  image_url: string;
  error?: string;
}

interface PptData {
  type: string;
  topic: string;
  slides: PptSlide[];
}

function parsePptContent(content: string): PptData | null {
  try {
    const parsed = JSON.parse(content);
    if (parsed?.type === "ppt_images" && Array.isArray(parsed.slides)) {
      return parsed as PptData;
    }
  } catch {
    // 不是 PPT 图片 JSON
  }
  return null;
}

export function PptImageGallery({ content }: { content: string }) {
  const data = useMemo(() => parsePptContent(content), [content]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);
  const [imageErrors, setImageErrors] = useState<Set<number>>(new Set());

  if (!data || data.slides.length === 0) return null;

  const currentSlide = data.slides[currentIndex];
  if (!currentSlide) return null;

  const totalSlides = data.slides.length;
  const validSlides = data.slides.filter((s) => s.image_url && !s.error);

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : totalSlides - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < totalSlides - 1 ? prev + 1 : 0));
  };

  const handleImageError = (index: number) => {
    setImageErrors((prev) => new Set(prev).add(index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setZoomedImage(null);
    if (e.key === "ArrowLeft") handlePrev();
    if (e.key === "ArrowRight") handleNext();
  };

  return (
    <div className="space-y-4" onKeyDown={handleKeyDown} tabIndex={0}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="shrink-0 rounded-full bg-[#6b7a8e] px-2.5 py-0.5 text-[11px] text-white">
            PPT 演示
          </span>
          <span className="text-sm font-medium text-[var(--color-warm-gray-800)]">
            {data.topic}
          </span>
        </div>
        <span className="text-xs text-[var(--color-warm-gray-400)]">
          {validSlides.length} 张图片 · 第 {currentIndex + 1}/{totalSlides} 页
        </span>
      </div>

      {/* 图片展示区 */}
      <div className="overflow-hidden rounded-xl bg-[var(--color-parchment)] ring-1 ring-[var(--color-warm-gray-200)]">
        {/* 主图 */}
        <div
          className="relative w-full cursor-pointer bg-[var(--color-warm-gray-100)]"
          style={{ aspectRatio: "16/9" }}
          onClick={() => {
            if (currentSlide.image_url && !imageErrors.has(currentIndex)) {
              setZoomedImage(currentSlide.image_url);
            }
          }}
        >
          {currentSlide.image_url && !imageErrors.has(currentIndex) ? (
            <img
              src={currentSlide.image_url}
              alt={currentSlide.title}
              className="h-full w-full object-contain"
              onError={() => handleImageError(currentIndex)}
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <div className="text-center">
                <p className="text-4xl">🖼️</p>
                <p className="mt-2 text-sm text-[var(--color-warm-gray-400)]">
                  {currentSlide.error
                    ? `图片生成失败：${currentSlide.error}`
                    : "图片加载中..."}
                </p>
              </div>
            </div>
          )}

          {/* 导航箭头 */}
          {totalSlides > 1 && (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePrev();
                }}
                className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 text-[var(--color-warm-gray-600)] shadow-sm ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-white hover:text-[var(--color-terracotta)]"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleNext();
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 text-[var(--color-warm-gray-600)] shadow-sm ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-white hover:text-[var(--color-terracotta)]"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </>
          )}

          {/* 页码指示器 */}
          {totalSlides > 1 && (
            <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
              {data.slides.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentIndex(idx);
                  }}
                  className={`h-2 rounded-full transition-all ${
                    idx === currentIndex
                      ? "w-5 bg-[var(--color-terracotta)]"
                      : "w-2 bg-white/70 hover:bg-white"
                  }`}
                />
              ))}
            </div>
          )}
        </div>

        {/* 当前页信息 */}
        <div className="border-t border-[var(--color-warm-gray-200)] px-4 py-3">
          <h4 className="mb-1 text-sm font-medium text-[var(--color-warm-gray-800)]">
            {currentSlide.title}
          </h4>
          {currentSlide.key_points.length > 0 && (
            <ul className="mb-2 space-y-0.5">
              {currentSlide.key_points.map((point, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-1.5 text-xs text-[var(--color-warm-gray-600)]"
                >
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[var(--color-terracotta)]" />
                  {point}
                </li>
              ))}
            </ul>
          )}
          {currentSlide.summary && (
            <p className="text-xs leading-5 text-[var(--color-warm-gray-500)]">
              💡 {currentSlide.summary}
            </p>
          )}
        </div>
      </div>

      {/* 缩略图导航 */}
      {totalSlides > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {data.slides.map((slide, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setCurrentIndex(idx)}
              className={`shrink-0 overflow-hidden rounded-lg ring-2 transition-all ${
                idx === currentIndex
                  ? "ring-[var(--color-terracotta)]"
                  : "ring-transparent hover:ring-[var(--color-warm-gray-300)]"
              }`}
              style={{ width: "100px", aspectRatio: "16/9" }}
            >
              {slide.image_url && !imageErrors.has(idx) ? (
                <img
                  src={slide.image_url}
                  alt={slide.title}
                  className="h-full w-full object-cover"
                  onError={() => handleImageError(idx)}
                  loading="lazy"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-[var(--color-warm-gray-100)] text-xs text-[var(--color-warm-gray-400)]">
                  N/A
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* 全屏预览 */}
      {zoomedImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setZoomedImage(null)}
        >
          <button
            type="button"
            onClick={() => setZoomedImage(null)}
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <img
            src={zoomedImage}
            alt="PPT 全屏预览"
            className="max-h-[90vh] max-w-[90vw] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
