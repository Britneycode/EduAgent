import { afterEach, describe, expect, it, vi } from "vitest";
import { streamChat, parseSSEChunk } from "@/lib/sse";

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

  it("routes proposed profile updates, progress and heartbeat events", async () => {
    const encoder = new TextEncoder();
    const onProfileUpdateProposed = vi.fn();
    const onProgress = vi.fn();
    const onHeartbeat = vi.fn();
    const onDone = vi.fn();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            [
              'data: {"type":"heartbeat","session_id":3,"payload":{}}',
              "",
              'data: {"type":"profile_update_proposed","session_id":3,"payload":{"session_id":3,"update":{"learning_goal":"复习反向传播"},"changed_fields":["learning_goal"]}}',
              "",
              'data: {"type":"progress","session_id":3,"payload":{"stage":"resources","completed":1,"total":2,"percent":50,"message":"已生成讲义"}}',
              "",
              'data: {"type":"done","session_id":3,"payload":{}}',
              "",
            ].join("\n")
          )
        );
        controller.close();
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body,
      })
    );

    await streamChat(3, "帮我复习反向传播", {
      onProfileUpdateProposed,
      onProgress,
      onHeartbeat,
      onDone,
    });

    expect(onHeartbeat).toHaveBeenCalledWith(3);
    expect(onProfileUpdateProposed).toHaveBeenCalledWith(
      {
        session_id: 3,
        update: { learning_goal: "复习反向传播" },
        changed_fields: ["learning_goal"],
      },
      3
    );
    expect(onProgress).toHaveBeenCalledWith(
      {
        stage: "resources",
        completed: 1,
        total: 2,
        percent: 50,
        message: "已生成讲义",
      },
      3
    );
    expect(onDone).toHaveBeenCalledWith(3);
  });

  it("parses complete SSE blocks and ignores incomplete chunks", () => {
    expect(
      parseSSEChunk('data: {"type":"heartbeat","session_id":1,"payload":{}}\n\n')
    ).toHaveLength(1);
    expect(parseSSEChunk("data: {")).toEqual([]);
  });
});
