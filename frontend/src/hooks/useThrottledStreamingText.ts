"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 流式文本渲染节流 Hook
 * 在高频 token 输入时，通过定时器批量更新，避免高频触发昂贵的 Markdown 重新解析
 * @param text 当前累计接收的流式文本
 * @param intervalMs 节流刷新间隔（默认 40ms），在保证人眼无感知流畅打字的同时大幅减少重渲染
 */
export function useThrottledStreamingText(text: string, intervalMs = 40): string {
  const [displayedText, setDisplayedText] = useState(text);
  const latestTextRef = useRef(text);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastUpdateRef = useRef<number>(0);

  // 当 text 被重置为空时，直接派生返回空串，无需在 effect 中同步 setState
  const activeText = text ? displayedText : "";

  useEffect(() => {
    latestTextRef.current = text;

    if (!text) {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      lastUpdateRef.current = 0;
      return;
    }

    const now = typeof performance !== "undefined" ? performance.now() : Date.now();
    const elapsed = now - lastUpdateRef.current;

    // 已经超过了节流间隔时间，安排刷新
    if (elapsed >= intervalMs) {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        lastUpdateRef.current = typeof performance !== "undefined" ? performance.now() : Date.now();
        setDisplayedText(latestTextRef.current);
      }, 0);
      return;
    }

    // 节流时间内到达的新 token，等待节流窗口结束时批量刷新
    if (timerRef.current === null) {
      const delay = Math.max(0, intervalMs - elapsed);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        lastUpdateRef.current = typeof performance !== "undefined" ? performance.now() : Date.now();
        setDisplayedText(latestTextRef.current);
      }, delay);
    }
  }, [text, intervalMs]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  return activeText;
}
