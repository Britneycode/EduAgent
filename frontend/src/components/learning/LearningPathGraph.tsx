"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { LearningPath, LearningPathNode } from "@/lib/types";

interface LearningPathGraphProps {
  path: LearningPath;
  onToggleNode: (node: LearningPathNode) => void;
}

export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  level: number;
  node: LearningPathNode;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface LearningPathGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width: number;
  height: number;
}

const STATUS_LABELS: Record<LearningPathNode["status"], string> = {
  pending: "待学习",
  in_progress: "学习中",
  completed: "已完成",
  skipped: "已跳过",
};

const STATUS_CLASSES: Record<LearningPathNode["status"], string> = {
  pending: "border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)] text-[var(--color-warm-gray-700)]",
  in_progress: "border-[#d6b66d] bg-[#fff8e6] text-[#7b5b18]",
  completed: "border-[var(--color-terracotta)] bg-[var(--color-terracotta)] text-white",
  skipped: "border-[var(--color-warm-gray-300)] bg-[var(--color-warm-gray-100)] text-[var(--color-warm-gray-500)]",
};

const NODE_WIDTH = 160;
const NODE_HEIGHT = 74;
const NODE_EDGE_OFFSET = NODE_WIDTH / 2 - 6;
const GRAPH_MIN_WIDTH = 640;
const GRAPH_MIN_HEIGHT = 260;
const GRAPH_X_MARGIN = NODE_WIDTH / 2 + 48;
const GRAPH_Y_MARGIN = 54;
const LEVEL_GAP = NODE_WIDTH + 82;
const ROW_GAP = 30;

function createEdges(nodes: LearningPathNode[]): GraphEdge[] {
  const concepts = new Set(nodes.map((node) => node.concept));
  const edges: GraphEdge[] = [];

  for (const node of nodes) {
    for (const prereq of node.prerequisites ?? []) {
      if (!concepts.has(prereq) || prereq === node.concept) continue;
      edges.push({
        id: `${prereq}->${node.concept}`,
        source: prereq,
        target: node.concept,
      });
    }
  }

  if (edges.length > 0 || nodes.length <= 1) {
    return edges;
  }

  return nodes.slice(1).map((node, index) => ({
    id: `${nodes[index].concept}->${node.concept}`,
    source: nodes[index].concept,
    target: node.concept,
  }));
}

export function buildLearningPathGraph(nodes: LearningPathNode[]): LearningPathGraphData {
  const edges = createEdges(nodes);
  const indexByConcept = new Map(nodes.map((node, index) => [node.concept, index]));
  const prereqsByConcept = new Map<string, string[]>();
  for (const edge of edges) {
    const prereqs = prereqsByConcept.get(edge.target) ?? [];
    prereqs.push(edge.source);
    prereqsByConcept.set(edge.target, prereqs);
  }

  const levelMemo = new Map<string, number>();
  const visiting = new Set<string>();

  function resolveLevel(concept: string): number {
    const memo = levelMemo.get(concept);
    if (memo !== undefined) return memo;
    if (visiting.has(concept)) {
      return indexByConcept.get(concept) ?? 0;
    }

    visiting.add(concept);
    const prereqs = prereqsByConcept.get(concept) ?? [];
    const level =
      prereqs.length === 0
        ? 0
        : Math.max(...prereqs.map((prereq) => resolveLevel(prereq) + 1));
    visiting.delete(concept);
    levelMemo.set(concept, level);
    return level;
  }

  const groups = new Map<number, LearningPathNode[]>();
  for (const node of nodes) {
    const level = resolveLevel(node.concept);
    const group = groups.get(level) ?? [];
    group.push(node);
    groups.set(level, group);
  }

  const levels = [...groups.keys()].sort((a, b) => a - b);
  for (const level of levels) {
    groups
      .get(level)
      ?.sort(
        (a, b) =>
          (indexByConcept.get(a.concept) ?? 0) - (indexByConcept.get(b.concept) ?? 0)
      );
  }

  const width = Math.max(
    GRAPH_MIN_WIDTH,
    Math.max(0, levels.length - 1) * LEVEL_GAP + GRAPH_X_MARGIN * 2
  );
  const maxGroupSize = Math.max(1, ...levels.map((level) => groups.get(level)?.length ?? 1));
  const maxGroupHeight =
    maxGroupSize * NODE_HEIGHT + Math.max(0, maxGroupSize - 1) * ROW_GAP;
  const height = Math.max(
    GRAPH_MIN_HEIGHT,
    maxGroupHeight + GRAPH_Y_MARGIN * 2
  );
  const graphNodes: GraphNode[] = [];

  levels.forEach((level, levelIndex) => {
    const group = groups.get(level) ?? [];
    const x =
      levels.length === 1
        ? width / 2
        : GRAPH_X_MARGIN +
          (levelIndex * (width - GRAPH_X_MARGIN * 2)) / (levels.length - 1);

    group.forEach((node, itemIndex) => {
      const groupHeight =
        group.length * NODE_HEIGHT + Math.max(0, group.length - 1) * ROW_GAP;
      const groupStartY = (height - groupHeight) / 2 + NODE_HEIGHT / 2;
      const y = groupStartY + itemIndex * (NODE_HEIGHT + ROW_GAP);
      graphNodes.push({
        id: node.concept,
        label: node.concept,
        x,
        y,
        level,
        node,
      });
    });
  });

  return {
    nodes: graphNodes,
    edges,
    width,
    height,
  };
}

export function calculateGraphScale(graphWidth: number, viewportWidth: number): number {
  void graphWidth;
  void viewportWidth;
  return 1;
}

function edgePath(source: GraphNode, target: GraphNode): string {
  const direction = target.x >= source.x ? 1 : -1;
  const startX = source.x + direction * NODE_EDGE_OFFSET;
  const endX = target.x - direction * NODE_EDGE_OFFSET;
  const curve = Math.max(70, Math.abs(endX - startX) * 0.45);
  return `M ${startX} ${source.y} C ${startX + direction * curve} ${source.y}, ${endX - direction * curve} ${target.y}, ${endX} ${target.y}`;
}

export function LearningPathGraph({ path, onToggleNode }: LearningPathGraphProps) {
  const graph = useMemo(() => buildLearningPathGraph(path.nodes), [path.nodes]);
  const viewportRef = useRef<HTMLDivElement>(null);
  const [viewportWidth, setViewportWidth] = useState(0);
  const nodesById = useMemo(
    () => new Map(graph.nodes.map((node) => [node.id, node])),
    [graph.nodes]
  );

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const syncWidth = () => {
      setViewportWidth(viewport.clientWidth);
    };

    syncWidth();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", syncWidth);
      return () => window.removeEventListener("resize", syncWidth);
    }

    const observer = new ResizeObserver(syncWidth);
    observer.observe(viewport);

    return () => observer.disconnect();
  }, []);

  if (path.nodes.length === 0) return null;

  const graphScale = calculateGraphScale(graph.width, viewportWidth);
  const scaledWidth = Math.ceil(graph.width * graphScale);
  const scaledHeight = Math.ceil(graph.height * graphScale);

  return (
    <div className="mb-4 min-w-0 rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-[var(--color-warm-gray-700)]">
            知识依赖图
          </h2>
          <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
            {graph.nodes.length} 个节点 · {graph.edges.length} 条依赖
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2 text-[11px] text-[var(--color-warm-gray-500)]">
          <span className="rounded-full bg-[var(--color-terracotta)] px-2 py-0.5 text-white">
            已完成
          </span>
          <span className="rounded-full bg-[#fff8e6] px-2 py-0.5 text-[#7b5b18] ring-1 ring-[#d6b66d]">
            学习中
          </span>
          <span className="rounded-full bg-[var(--color-warm-gray-50)] px-2 py-0.5 ring-1 ring-[var(--color-warm-gray-200)]">
            待学习
          </span>
        </div>
      </div>

      <div ref={viewportRef} className="max-w-full overflow-x-auto pb-1">
        <div
          className="relative mx-auto"
          style={{ width: scaledWidth, height: scaledHeight }}
        >
          <div
            className="relative"
            style={{
              width: graph.width,
              height: graph.height,
              transform: `scale(${graphScale})`,
              transformOrigin: "top left",
            }}
          >
            <svg
              className="absolute inset-0"
              width={graph.width}
              height={graph.height}
              viewBox={`0 0 ${graph.width} ${graph.height}`}
              role="img"
              aria-label={`${path.title} 知识依赖图`}
            >
              <defs>
                <marker
                  id={`arrow-${path.id}`}
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="4"
                  orient="auto"
                >
                  <path d="M 0 0 L 8 4 L 0 8 z" fill="#c8c4b8" />
                </marker>
              </defs>
              {graph.edges.map((edge) => {
                const source = nodesById.get(edge.source);
                const target = nodesById.get(edge.target);
                if (!source || !target) return null;
                return (
                  <path
                    key={edge.id}
                    d={edgePath(source, target)}
                    fill="none"
                    stroke="#c8c4b8"
                    strokeWidth={2}
                    markerEnd={`url(#arrow-${path.id})`}
                  />
                );
              })}
            </svg>

            {graph.nodes.map((item) => {
              const isGoal = item.node.concept === path.goal_topic;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onToggleNode(item.node)}
                  className={`absolute h-[74px] w-40 -translate-x-1/2 -translate-y-1/2 rounded-xl border px-3 py-2 text-left shadow-sm transition-transform hover:scale-[1.02] ${STATUS_CLASSES[item.node.status]}`}
                  style={{ left: item.x, top: item.y }}
                  title={item.node.description || item.node.concept}
                >
                  <span className="mb-1 flex items-center justify-between gap-2">
                    <span className="truncate text-[11px] opacity-75">
                      {STATUS_LABELS[item.node.status]}
                    </span>
                    {isGoal && (
                      <span className="shrink-0 rounded-full bg-black/10 px-1.5 py-0.5 text-[10px]">
                        目标
                      </span>
                    )}
                  </span>
                  <span className="line-clamp-2 break-words text-sm font-medium leading-5">
                    {item.label}
                  </span>
                  {item.node.chapter && (
                    <span className="mt-1 block truncate text-[10px] opacity-65">
                      {item.node.chapter} · {item.node.section}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
