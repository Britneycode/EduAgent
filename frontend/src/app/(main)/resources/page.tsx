"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  ResourceResponse,
  ResourceType,
} from "@/lib/types";
import { ResourceCard } from "@/components/chat/ResourceCard";
import { fetchResources } from "@/lib/api";

const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  document: "学习文档",
  quiz: "练习题",
  code: "代码实践",
  mindmap: "思维导图",
  ppt: "教学演示",
  ppt_images: "PPT演示",
  animation: "算法动画",
  reading: "拓展阅读",
};

const RESOURCE_TYPE_COLORS: Record<ResourceType, string> = {
  document: "bg-[var(--color-terracotta)]",
  quiz: "bg-[#6b8e6b]",
  code: "bg-[#7a6e5d]",
  mindmap: "bg-[#8b7355]",
  ppt: "bg-[#9b6b4a]",
  ppt_images: "bg-[#6b7a8e]",
  animation: "bg-[#6b7a8e]",
  reading: "bg-[#8e6b7a]",
};

const ALL_TYPES: ResourceType[] = [
  "document",
  "quiz",
  "code",
  "mindmap",
  "ppt",
  "ppt_images",
  "animation",
  "reading",
];

export default function ResourcesPage() {
  const [resources, setResources] = useState<ResourceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<ResourceType | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const handleFilterChange = (nextFilter: ResourceType | null) => {
    if (filter === nextFilter) return;
    setLoading(true);
    setFilter(nextFilter);
  };

  useEffect(() => {
    let cancelled = false;

    fetchResources(filter)
      .then((nextResources) => {
        if (!cancelled) setResources(nextResources);
      })
      .catch(() => {
        if (!cancelled) setResources([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filter]);

  const visibleResources = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    if (!keyword) return resources;

    return resources.filter((resource) => {
      const haystack = [
        resource.title,
        resource.content,
        resource.knowledge_point,
        resource.agent_name,
      ]
        .filter(Boolean)
        .join("\n")
        .toLowerCase();
      return haystack.includes(keyword);
    });
  }, [resources, searchQuery]);

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-8">
        <h1 className="mb-6 text-2xl text-[var(--color-warm-gray-800)] font-serif">
          资源中心
        </h1>

        <div className="mb-4">
          <input
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="搜索标题、知识点或资源内容..."
            className="w-full rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
          />
        </div>

        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => handleFilterChange(null)}
            className={`rounded-full px-3 py-1.5 text-xs transition-colors ${
              filter === null
                ? "bg-[var(--color-terracotta)] text-white"
                : "bg-[var(--color-ivory)] text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] hover:bg-[var(--color-parchment)]"
            }`}
          >
            全部
          </button>
          {ALL_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => handleFilterChange(type)}
              className={`rounded-full px-3 py-1.5 text-xs transition-colors ${
                filter === type
                  ? "bg-[var(--color-terracotta)] text-white"
                  : "bg-[var(--color-ivory)] text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] hover:bg-[var(--color-parchment)]"
              }`}
            >
              {RESOURCE_TYPE_LABELS[type]}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="py-16 text-center text-sm text-[var(--color-warm-gray-400)]">
            正在加载资源...
          </p>
        ) : visibleResources.length === 0 ? (
          <div className="py-16 text-center">
            <p className="mb-2 text-sm text-[var(--color-warm-gray-500)]">
              {resources.length === 0 ? "暂无学习资源" : "没有匹配的学习资源"}
            </p>
            <p className="text-xs text-[var(--color-warm-gray-400)]">
              {resources.length === 0
                ? "在对话中发送学习请求，系统会自动生成个性化学习资源。"
                : "调整搜索词或资源类型筛选后再试。"}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {visibleResources.map((r) => {
              const isExpanded = expandedId === r.id;
              const typeLabel = RESOURCE_TYPE_LABELS[r.resource_type] ?? r.resource_type;
              const colorClass =
                RESOURCE_TYPE_COLORS[r.resource_type] ?? "bg-[var(--color-terracotta)]";

              return (
                <div
                  key={r.id}
                  className="rounded-xl bg-[var(--color-ivory)] ring-1 ring-[var(--color-warm-gray-200)]"
                >
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : r.id)}
                    className="flex w-full items-center gap-3 px-5 py-4 text-left"
                  >
                    <span
                      className={`shrink-0 rounded-full ${colorClass} px-2.5 py-0.5 text-[11px] text-white`}
                    >
                      {typeLabel}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-[var(--color-warm-gray-800)]">
                        {r.is_favorite ? "★ " : ""}{r.title}
                      </div>
                      <div className="mt-0.5 flex items-center gap-3 text-xs text-[var(--color-warm-gray-400)]">
                        {r.knowledge_point && <span>知识点：{r.knowledge_point}</span>}
                        <span>{new Date(r.created_at).toLocaleString("zh-CN")}</span>
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-[var(--color-warm-gray-400)]">
                      {isExpanded ? "收起" : "展开"}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-[var(--color-warm-gray-200)] px-5 pb-4">
                      <ResourceCard resource={r} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
