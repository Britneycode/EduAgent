"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function MainError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // 可以在此记录日志
    console.error("页面加载错误:", error);
  }, [error]);

  return (
    <div className="flex h-full min-h-[50vh] flex-col items-center justify-center p-6 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-warm-gray-100)] text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
        <AlertCircle className="h-6 w-6" />
      </div>
      <h3 className="font-serif text-lg font-medium text-[var(--color-warm-gray-800)]">
        页面加载出现问题
      </h3>
      <p className="mt-2 max-w-md text-xs leading-5 text-[var(--color-warm-gray-500)]">
        {error.message || "未能成功加载请求的页面内容，请检查网络后重试。"}
      </p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)]"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        重新加载
      </button>
    </div>
  );
}
