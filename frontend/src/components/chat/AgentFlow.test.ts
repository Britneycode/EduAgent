import { describe, expect, it } from "vitest";
import { buildAgentFlowSteps } from "@/components/chat/AgentFlow";

describe("buildAgentFlowSteps", () => {
  it("marks the latest running agent as active", () => {
    const steps = buildAgentFlowSteps(
      [
        {
          agent: "RouterAgent",
          status: "working",
          message: "正在识别学习意图",
        },
        {
          agent: "PlannerAgent",
          status: "working",
          message: "正在拆解资源生成任务",
        },
      ],
      [],
      true
    );

    expect(steps.map((step) => [step.agent, step.state])).toEqual([
      ["RouterAgent", "done"],
      ["PlannerAgent", "active"],
    ]);
  });

  it("adds completed resource agents from resource cards", () => {
    const steps = buildAgentFlowSteps(
      [{ agent: "PlannerAgent", status: "working", message: "并行生成" }],
      [
        {
          id: 1,
          resource_type: "document",
          title: "搜索算法讲义",
          content: "",
          agent_name: "DocAgent",
        },
        {
          id: 2,
          resource_type: "mindmap",
          title: "搜索算法导图",
          content: "",
          agent_name: "MediaAgent",
        },
        {
          id: 3,
          resource_type: "ppt",
          title: "搜索算法演示",
          content: "",
          agent_name: "MediaAgent",
        },
      ],
      true
    );

    expect(steps.map((step) => [step.agent, step.state])).toEqual([
      ["PlannerAgent", "active"],
      ["DocAgent", "done"],
      ["MediaAgent", "done"],
    ]);
    expect(steps.at(-1)?.message).toBe("已生成 2 个资源");
  });
});
