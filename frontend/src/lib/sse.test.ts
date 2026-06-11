import { afterEach, describe, expect, it, vi } from "vitest";
import { streamChat } from "@/lib/sse";

describe("streamChat", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports an error when fetch fails before a response is available", async () => {
    const onError = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("network down"))
    );

    await streamChat(1, "帮我复习反向传播", { onError });

    expect(onError).toHaveBeenCalledWith(
      { message: "连接服务器失败，请检查网络" },
      1
    );
  });

  it("finishes cleanly when the request is aborted before a response", async () => {
    const controller = new AbortController();
    const onDone = vi.fn();
    const onError = vi.fn();
    controller.abort();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError"))
    );

    await streamChat(2, "帮我复习反向传播", { onDone, onError }, controller.signal);

    expect(onDone).toHaveBeenCalledWith(2);
    expect(onError).not.toHaveBeenCalled();
  });
});
