import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useThrottledStreamingText } from "./useThrottledStreamingText";

describe("useThrottledStreamingText", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("首次传入内容时立即显示", () => {
    const { result } = renderHook(({ text }) => useThrottledStreamingText(text, 50), {
      initialProps: { text: "Hello" },
    });

    expect(result.current).toBe("Hello");
  });

  it("短时间内高频输入会进行节流合并并在定时周期到达后更新", () => {
    const { result, rerender } = renderHook(
      ({ text }) => useThrottledStreamingText(text, 50),
      {
        initialProps: { text: "A" },
      }
    );

    expect(result.current).toBe("A");

    // 高频连续追加字符
    rerender({ text: "AB" });
    rerender({ text: "ABC" });
    rerender({ text: "ABCD" });

    // 尚未经过 50ms 时，仍维持节流前的视图，避免高频重解析
    expect(result.current).toBe("A");

    // 时间推移 50ms 后，批量刷新到最新内容
    act(() => {
      vi.advanceTimersByTime(50);
    });

    expect(result.current).toBe("ABCD");
  });

  it("文本清空时立即响应重置", () => {
    const { result, rerender } = renderHook(
      ({ text }) => useThrottledStreamingText(text, 50),
      {
        initialProps: { text: "Some text" },
      }
    );

    expect(result.current).toBe("Some text");

    rerender({ text: "" });
    expect(result.current).toBe("");
  });
});
