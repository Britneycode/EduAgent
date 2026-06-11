import { describe, expect, it } from "vitest";
import {
  createChatStreamStore,
  getStreamStateForSession,
} from "@/store/chatStreamStore";

describe("chatStreamStore", () => {
  it("缺失会话流状态时返回稳定的空对象", () => {
    const store = createChatStreamStore();

    const first = getStreamStateForSession(store.getState().streams, 99);
    const second = getStreamStateForSession(store.getState().streams, 99);

    expect(first).toBe(second);
    expect(first).toMatchObject({
      isStreaming: false,
      streamingContent: "",
      agentName: "",
      agentStatus: null,
      agentTimeline: [],
      resources: [],
      wikiFallback: null,
      error: null,
    });
  });

  it("在会话切换后仍保留原会话的流式状态", () => {
    const store = createChatStreamStore();

    store.getState().startStream(1);
    store.getState().appendToken(1, "你好");
    store.getState().setAgentStatus(1, "Tutor", "正在生成回答");

    store.getState().startStream(2);
    store.getState().appendToken(2, "新的会话内容");

    const sessionOne = store.getState().streams[1];
    const sessionTwo = store.getState().streams[2];

    expect(sessionOne).toMatchObject({
      isStreaming: true,
      streamingContent: "你好",
      agentName: "Tutor",
      agentStatus: "正在生成回答",
      agentTimeline: [
        {
          agent: "Tutor",
          status: "working",
          message: "正在生成回答",
        },
      ],
    });
    expect(sessionTwo).toMatchObject({
      isStreaming: true,
      streamingContent: "新的会话内容",
    });
  });

  it("结束流式后保留已生成内容并清空控制器", () => {
    const store = createChatStreamStore();
    const controller = new AbortController();

    store.getState().startStream(3);
    store.getState().appendToken(3, "已生成内容");
    store.getState().setController(3, controller);
    store.getState().finishStream(3);

    expect(store.getState().streams[3]).toMatchObject({
      isStreaming: false,
      streamingContent: "已生成内容",
    });
    expect(store.getState().controllers[3]).toBeNull();
  });

  it("完成后保留资源卡片和兜底提示，直到下次 clear", () => {
    const store = createChatStreamStore();

    store.getState().startStream(4);
    store.getState().appendToken(4, "回答");
    store.getState().setResources(4, [
      {
        id: 1,
        resource_type: "document",
        title: "资料",
        content: "内容",
      },
    ]);
    store.getState().setWikiFallback(4, "已使用知识库兜底");
    store.getState().finishStream(4);

    expect(store.getState().streams[4]).toMatchObject({
      isStreaming: false,
      streamingContent: "回答",
      resources: [
        {
          id: 1,
          resource_type: "document",
          title: "资料",
          content: "内容",
        },
      ],
      wikiFallback: "已使用知识库兜底",
    });
  });

  it("同一个 Agent 的状态会更新而不是重复追加", () => {
    const store = createChatStreamStore();

    store.getState().startStream(5);
    store.getState().setAgentStatus(5, "PlannerAgent", "正在拆解任务");
    store.getState().setAgentStatus(5, "PlannerAgent", "正在并行生成资源");
    store.getState().setAgentStatus(5, "DocAgent", "正在生成学习文档");

    expect(store.getState().streams[5].agentTimeline).toEqual([
      {
        agent: "PlannerAgent",
        status: "working",
        message: "正在并行生成资源",
      },
      {
        agent: "DocAgent",
        status: "working",
        message: "正在生成学习文档",
      },
    ]);
  });
});

