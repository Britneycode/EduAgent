import { describe, expect, it } from "vitest";
import {
  buildLearningPathGraph,
  calculateGraphScale,
} from "@/components/learning/LearningPathGraph";
import type { LearningPathNode } from "@/lib/types";

function node(
  concept: string,
  prerequisites: string[] = [],
  status: LearningPathNode["status"] = "pending"
): LearningPathNode {
  return {
    concept,
    chapter: "ch",
    section: "s",
    description: "",
    prerequisites,
    status,
  };
}

describe("buildLearningPathGraph", () => {
  it("builds prerequisite edges and layered positions", () => {
    const graph = buildLearningPathGraph([
      node("梯度下降"),
      node("多层感知机", ["梯度下降"]),
      node("反向传播", ["梯度下降", "多层感知机"], "completed"),
    ]);

    expect(graph.edges.map((edge) => edge.id)).toEqual([
      "梯度下降->多层感知机",
      "梯度下降->反向传播",
      "多层感知机->反向传播",
    ]);
    const levels = new Map(graph.nodes.map((item) => [item.id, item.level]));
    expect(levels.get("梯度下降")).toBe(0);
    expect(levels.get("多层感知机")).toBe(1);
    expect(levels.get("反向传播")).toBe(2);
  });

  it("falls back to sequential edges for historical paths without prerequisites", () => {
    const graph = buildLearningPathGraph([
      node("A"),
      { ...node("B"), prerequisites: undefined },
      { ...node("C"), prerequisites: undefined },
    ]);

    expect(graph.edges.map((edge) => edge.id)).toEqual(["A->B", "B->C"]);
  });

  it("keeps a common five-step path readable with horizontal scrolling", () => {
    const graph = buildLearningPathGraph([
      node("计算机网络概述"),
      node("分层体系结构", ["计算机网络概述"]),
      node("数据链路层", ["分层体系结构"]),
      node("以太网", ["数据链路层"]),
      node("交换机转发", ["以太网"]),
    ]);

    const sortedNodes = [...graph.nodes].sort((a, b) => a.x - b.x);
    const gaps = sortedNodes.slice(1).map((item, index) => item.x - sortedNodes[index].x);

    expect(graph.width).toBeGreaterThan(960);
    expect(Math.min(...gaps)).toBeGreaterThanOrEqual(220);
  });

  it("keeps graph scale at 1 so oversized graphs use horizontal scrolling", () => {
    expect(calculateGraphScale(928, 696)).toBe(1);
    expect(calculateGraphScale(640, 696)).toBe(1);
    expect(calculateGraphScale(928, 0)).toBe(1);
  });
});
