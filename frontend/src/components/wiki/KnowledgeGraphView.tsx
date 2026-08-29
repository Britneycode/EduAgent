"use client";

import { useMemo, useState, useRef, useCallback, useEffect } from "react";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import type { WikiConceptNode } from "@/lib/types";

export interface WikiGraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  level: number;
  concept: WikiConceptNode;
}

export interface WikiGraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface WikiGraphData {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
  width: number;
  height: number;
}

function createEdges(concepts: WikiConceptNode[]): WikiGraphEdge[] {
  const names = new Set(concepts.map((concept) => concept.name));
  const edges: WikiGraphEdge[] = [];

  for (const concept of concepts) {
    for (const prereq of concept.prerequisites ?? []) {
      if (!names.has(prereq) || prereq === concept.name) continue;
      edges.push({
        id: `${prereq}->${concept.name}`,
        source: prereq,
        target: concept.name,
      });
    }
  }

  if (edges.length > 0 || concepts.length <= 1) {
    return edges;
  }

  return concepts.slice(1).map((concept, index) => ({
    id: `${concepts[index].name}->${concept.name}`,
    source: concepts[index].name,
    target: concept.name,
  }));
}

export function buildWikiGraph(concepts: WikiConceptNode[]): WikiGraphData {
  const edges = createEdges(concepts);
  const indexByName = new Map(
    concepts.map((concept, index) => [concept.name, index])
  );
  const prereqsByName = new Map<string, string[]>();

  for (const edge of edges) {
    const prereqs = prereqsByName.get(edge.target) ?? [];
    prereqs.push(edge.source);
    prereqsByName.set(edge.target, prereqs);
  }

  const levelMemo = new Map<string, number>();
  const visiting = new Set<string>();

  function resolveLevel(name: string): number {
    const memo = levelMemo.get(name);
    if (memo !== undefined) return memo;
    if (visiting.has(name)) {
      return indexByName.get(name) ?? 0;
    }

    visiting.add(name);
    const prereqs = prereqsByName.get(name) ?? [];
    const level =
      prereqs.length === 0
        ? 0
        : Math.max(...prereqs.map((prereq) => resolveLevel(prereq) + 1));
    visiting.delete(name);
    levelMemo.set(name, level);
    return level;
  }

  const groups = new Map<number, WikiConceptNode[]>();
  for (const concept of concepts) {
    const level = resolveLevel(concept.name);
    const group = groups.get(level) ?? [];
    group.push(concept);
    groups.set(level, group);
  }

  const levels = [...groups.keys()].sort((a, b) => a - b);
  for (const level of levels) {
    groups
      .get(level)
      ?.sort(
        (a, b) =>
          (indexByName.get(a.name) ?? 0) - (indexByName.get(b.name) ?? 0)
      );
  }

  const width = Math.max(780, Math.max(0, levels.length - 1) * 220 + 220);
  const maxGroupSize = Math.max(
    1,
    ...levels.map((level) => groups.get(level)?.length ?? 1)
  );
  const height = Math.max(300, maxGroupSize * 92 + 120);
  const nodes: WikiGraphNode[] = [];

  levels.forEach((level, levelIndex) => {
    const group = groups.get(level) ?? [];
    const x =
      levels.length === 1
        ? width / 2
        : 110 + (levelIndex * (width - 220)) / (levels.length - 1);

    group.forEach((concept, itemIndex) => {
      const y =
        group.length === 1
          ? height / 2
          : 70 + (itemIndex * (height - 140)) / (group.length - 1);
      nodes.push({
        id: concept.name,
        label: concept.name,
        x,
        y,
        level,
        concept,
      });
    });
  });

  return { nodes, edges, width, height };
}

function edgePath(source: WikiGraphNode, target: WikiGraphNode): string {
  const direction = target.x >= source.x ? 1 : -1;
  const startX = source.x + direction * 76;
  const endX = target.x - direction * 76;
  const curve = Math.max(68, Math.abs(endX - startX) * 0.42);
  return `M ${startX} ${source.y} C ${startX + direction * curve} ${source.y}, ${endX - direction * curve} ${target.y}, ${endX} ${target.y}`;
}

interface KnowledgeGraphViewProps {
  concepts: WikiConceptNode[];
  selectedConcept: string | null;
  onSelectConcept: (concept: WikiConceptNode) => void;
}

export function KnowledgeGraphView({
  concepts,
  selectedConcept,
  onSelectConcept,
}: KnowledgeGraphViewProps) {
  const graph = useMemo(() => buildWikiGraph(concepts), [concepts]);
  const nodesById = useMemo(
    () => new Map(graph.nodes.map((node) => [node.id, node])),
    [graph.nodes]
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const hasMovedRef = useRef(false);

  const handleZoomIn = () => setZoom((prev) => Math.min(1.8, Number((prev + 0.15).toFixed(2))));
  const handleZoomOut = () => setZoom((prev) => Math.max(0.5, Number((prev - 0.15).toFixed(2))));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // 仅左键拖拽
    setIsDragging(true);
    hasMovedRef.current = false;
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      const newX = e.clientX - dragStartRef.current.x;
      const newY = e.clientY - dragStartRef.current.y;
      if (Math.abs(newX - pan.x) > 3 || Math.abs(newY - pan.y) > 3) {
        hasMovedRef.current = true;
      }
      setPan({ x: newX, y: newY });
    },
    [isDragging, pan.x, pan.y]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      return () => {
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // 滚轮缩放支持 (按住 Ctrl/Meta 缩放或平移)
  const handleWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoom((prev) => Math.min(1.8, Math.max(0.5, Number((prev + delta).toFixed(2)))));
    }
  };

  if (concepts.length === 0) return null;

  return (
    <section className="mb-6 rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)] select-none">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-[var(--color-warm-gray-700)]">
            知识图谱
          </h2>
          <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
            {graph.nodes.length} 个知识点 · {graph.edges.length} 条依赖 · 可拖拽平移与缩放
          </p>
        </div>

        {/* 缩放与控制器 */}
        <div className="flex items-center gap-1.5 rounded-lg bg-[var(--color-parchment)] p-1 ring-1 ring-[var(--color-warm-gray-200)]">
          <button
            type="button"
            onClick={handleZoomOut}
            className="flex h-7 w-7 items-center justify-center rounded text-[var(--color-warm-gray-600)] transition-colors hover:bg-[var(--color-warm-gray-100)] hover:text-[var(--color-terracotta)]"
            title="缩小"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <span className="min-w-[42px] text-center text-xs font-medium text-[var(--color-warm-gray-600)]">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={handleZoomIn}
            className="flex h-7 w-7 items-center justify-center rounded text-[var(--color-warm-gray-600)] transition-colors hover:bg-[var(--color-warm-gray-100)] hover:text-[var(--color-terracotta)]"
            title="放大"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <div className="mx-0.5 h-3.5 w-px bg-[var(--color-warm-gray-200)]" />
          <button
            type="button"
            onClick={handleReset}
            className="flex h-7 w-7 items-center justify-center rounded text-[var(--color-warm-gray-600)] transition-colors hover:bg-[var(--color-warm-gray-100)] hover:text-[var(--color-terracotta)]"
            title="重置视角"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onWheel={handleWheel}
        className={`relative h-[360px] w-full overflow-hidden rounded-lg bg-[var(--color-warm-gray-50)]/50 ring-1 ring-inset ring-[var(--color-warm-gray-200)]/60 ${
          isDragging ? "cursor-grabbing" : "cursor-grab"
        }`}
      >
        <div
          className="absolute inset-0 origin-center transition-transform duration-75 ease-out"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            width: graph.width,
            height: graph.height,
          }}
        >
          <svg
            className="absolute inset-0 pointer-events-none"
            width={graph.width}
            height={graph.height}
            viewBox={`0 0 ${graph.width} ${graph.height}`}
            role="img"
            aria-label="章节知识图谱"
          >
            <defs>
              <marker
                id="wiki-graph-arrow"
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
                  markerEnd="url(#wiki-graph-arrow)"
                />
              );
            })}
          </svg>

          {graph.nodes.map((item) => {
            const selected = selectedConcept === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={(e) => {
                  // 如果发生了拖拽位移，不触发选中
                  if (hasMovedRef.current) {
                    e.preventDefault();
                    return;
                  }
                  onSelectConcept(item.concept);
                }}
                className={`absolute h-[72px] w-40 -translate-x-1/2 -translate-y-1/2 rounded-xl border px-3 py-2 text-left shadow-sm transition-transform hover:scale-[1.02] ${
                  selected
                    ? "border-[var(--color-terracotta)] bg-[var(--color-terracotta)] text-white shadow-md ring-2 ring-[var(--color-terracotta)]/20"
                    : "border-[var(--color-warm-gray-200)] bg-[var(--color-parchment)] text-[var(--color-warm-gray-700)] hover:border-[var(--color-warm-gray-300)]"
                }`}
                style={{ left: item.x, top: item.y }}
                title={item.concept.description || item.label}
              >
                <span
                  className={`mb-1 block truncate text-[10px] ${
                    selected
                      ? "text-white/75"
                      : "text-[var(--color-warm-gray-400)]"
                  }`}
                >
                  Level {item.level + 1}
                </span>
                <span className="line-clamp-2 break-words text-sm font-medium leading-5">
                  {item.label}
                </span>
                {item.concept.section && (
                  <span
                    className={`mt-1 block truncate text-[10px] ${
                      selected
                        ? "text-white/70"
                        : "text-[var(--color-warm-gray-400)]"
                    }`}
                  >
                    {item.concept.section}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
