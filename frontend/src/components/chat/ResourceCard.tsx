"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BookOpenText,
  ChevronDown,
  ChevronUp,
  Code2,
  Download,
  ExternalLink,
  FileQuestion,
  FileText,
  Film,
  Flag,
  GitBranch,
  Newspaper,
  PackageOpen,
  PlayCircle,
  Presentation,
  RefreshCw,
  Share2,
  Square,
  Star,
  Volume2,
} from "lucide-react";
import type {
  ResourceCard as ResourceCardType,
  ResourceSource,
  ResourceType,
} from "@/lib/types";
import {
  createAnimationExportAsset,
  exportResourceMarkdown,
  exportResourcePptx,
  fetchAssetBlob,
  fetchResourceSpeech,
  regenerateResource,
  setResourceFavorite,
} from "@/lib/api";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";
import { MermaidRenderer } from "@/components/ui/MermaidRenderer";
import { SlideViewer } from "@/components/ui/SlideViewer";
import { AnimationPlayer } from "@/components/ui/AnimationPlayer";
import { CodeRunner } from "@/components/ui/CodeRunner";
import { PptImageGallery } from "@/components/ui/PptImageGallery";
import { InteractiveQuiz } from "@/components/chat/InteractiveQuiz";

const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  document: "学习文档",
  quiz: "练习题",
  code: "代码实践",
  mindmap: "思维导图",
  ppt: "教学演示",
  ppt_images: "教学演示",
  animation: "算法动画",
  video: "相关视频",
  reading: "拓展阅读",
};

const RESOURCE_TYPE_COLORS: Record<ResourceType, string> = {
  document: "bg-[var(--color-resource-document)]",
  quiz: "bg-[var(--color-resource-quiz)]",
  code: "bg-[var(--color-resource-code)]",
  mindmap: "bg-[var(--color-resource-mindmap)]",
  ppt: "bg-[var(--color-resource-ppt)]",
  ppt_images: "bg-[var(--color-resource-ppt)]",
  animation: "bg-[var(--color-resource-media)]",
  video: "bg-[#536b7c]",
  reading: "bg-[var(--color-resource-reading)]",
};

const RESOURCE_TYPE_ICONS = {
  document: BookOpenText,
  quiz: FileQuestion,
  code: Code2,
  mindmap: GitBranch,
  ppt: Presentation,
  ppt_images: Presentation,
  animation: Film,
  video: Film,
  reading: Newspaper,
};

interface ResourceCardProps {
  resource: ResourceCardType;
  sessionId?: number | null;
}

function extractMermaidBlocks(content: string): { mermaidCode: string | null; rest: string } {
  const regex = /```mermaid\s*\n([\s\S]*?)```/;
  const match = content.match(regex);
  if (!match) return { mermaidCode: null, rest: content };
  const mermaidCode = match[1].trim();
  const rest = content.replace(regex, "").trim();
  return { mermaidCode, rest };
}

interface VideoResultItem {
  title: string;
  url: string;
  platform: string;
  reason: string;
  summary: string;
}

function parseVideoResults(content: string): VideoResultItem[] {
  const results: VideoResultItem[] = [];
  const lines = content.split(/\r?\n/);
  let current: VideoResultItem | null = null;

  for (const line of lines) {
    const linkMatch = line.match(
      /^\s*\d+\.\s+\[(.+?)\]\((https?:\/\/(?:[\w-]+\.)?bilibili\.com\/(?:video|bangumi\/play)\/[^\s)]+)\)/
    );
    if (linkMatch) {
      if (current) results.push(current);
      current = {
        title: linkMatch[1].trim(),
        url: linkMatch[2].trim(),
        platform: "B站",
        reason: "",
        summary: "",
      };
      continue;
    }

    if (!current) continue;
    const detailMatch = line.match(/^\s*[-*]\s*(平台|推荐理由|摘要)\s*[:：]\s*(.+)$/);
    if (!detailMatch) continue;
    const key = detailMatch[1];
    const value = detailMatch[2].trim();
    if (key === "平台") current.platform = value;
    if (key === "推荐理由") current.reason = value;
    if (key === "摘要") current.summary = value;
  }

  if (current) results.push(current);
  return results;
}

function getVideoNotice(content: string): { tone: "warning" | "empty"; text: string } | null {
  if (!content.includes("视频搜索暂不可用") && !content.includes("暂未在 B站检索到")) {
    return null;
  }

  const text = content
    .replace(/^#.+$/gm, "")
    .replace(/^[-*]\s*/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (content.includes("视频搜索暂不可用")) {
    return {
      tone: "warning",
      text: text || "视频搜索暂不可用，请稍后重试。",
    };
  }

  return {
    tone: "empty",
    text: text || "暂未找到足够匹配的 B站视频。换个更具体的关键词后可以重试。",
  };
}

function VideoResourceContent({ content }: { content: string }) {
  const videos = parseVideoResults(content);
  const notice = getVideoNotice(content);

  if (videos.length === 0) {
    if (notice) {
      return (
        <div
          className={`rounded-xl px-4 py-3 text-sm leading-6 shadow-[var(--shadow-ring)] ${
            notice.tone === "warning"
              ? "bg-amber-50 text-amber-800"
              : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-600)]"
          }`}
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="whitespace-pre-wrap">{notice.text}</p>
          </div>
        </div>
      );
    }
    return <MarkdownRenderer content={content} />;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm leading-6 text-[var(--color-warm-gray-600)]">
        以下结果来自 B站公开搜索结果，按当前知识点整理为可继续学习的视频清单。
      </p>
      <div className="space-y-2.5">
        {videos.map((video, index) => (
          <article
            key={`${video.url}-${index}`}
            className="rounded-xl bg-[var(--color-parchment)]/70 p-3 shadow-[var(--shadow-ring)]"
          >
            <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#536b7c] px-2 py-0.5 text-[11px] text-white">
                    <Film className="h-3 w-3" />
                    {video.platform || "B站"}
                  </span>
                  <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                    视频 {index + 1}
                  </span>
                </div>
                <a
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex max-w-full items-center gap-1.5 text-[15px] font-medium leading-6 text-[var(--color-warm-gray-800)] underline-offset-4 hover:text-[var(--color-terracotta)] hover:underline"
                >
                  <span className="break-words">{video.title}</span>
                  <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                </a>
              </div>
              <a
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg bg-[var(--color-terracotta)] px-3 text-xs text-white hover:bg-[var(--color-terracotta-hover)]"
              >
                <PlayCircle className="h-3.5 w-3.5" />
                打开 B站
              </a>
            </div>
            <div className="grid gap-2 text-sm leading-6 text-[var(--color-warm-gray-600)] md:grid-cols-2">
              <div className="rounded-lg bg-[var(--color-ivory)]/75 px-3 py-2">
                <p className="mb-0.5 text-[11px] text-[var(--color-warm-gray-400)]">
                  推荐理由
                </p>
                <p>{video.reason || "与当前学习主题相关，适合作为补充讲解视频。"}</p>
              </div>
              <div className="rounded-lg bg-[var(--color-ivory)]/75 px-3 py-2">
                <p className="mb-0.5 text-[11px] text-[var(--color-warm-gray-400)]">
                  摘要
                </p>
                <p>{video.summary || "该视频标题与当前学习主题相关，可作为补充学习材料。"}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

interface TrustedSource {
  index: number;
  label: string;
  score: number | null;
  chunkId?: string;
  snippet?: string;
  sourceName?: string;
}

interface TrustedCitationData {
  content: string;
  confidence: number | null;
  warning: string | null;
  sources: TrustedSource[];
}

function buildTrustedCitationData(resource: ResourceCardType): TrustedCitationData {
  const parsed = parseMarkdownCitationBlock(resource.content);
  const structuredSources = normalizeStructuredSources(resource.sources);
  const sources = structuredSources.length > 0 ? structuredSources : parsed.sources;
  const confidence =
    typeof resource.confidence === "number" ? resource.confidence : parsed.confidence;
  const warning =
    parsed.warning ||
    (typeof confidence === "number" && confidence < 0.3
      ? "知识库命中置信度较低，请优先核对来源片段。"
      : null);

  return {
    content: parsed.content,
    confidence,
    warning,
    sources,
  };
}

function parseMarkdownCitationBlock(content: string): TrustedCitationData {
  const marker = "**参考来源：**";
  const markerIndex = content.indexOf(marker);
  if (markerIndex === -1) {
    return { content, confidence: null, warning: null, sources: [] };
  }

  const dividerIndex = content.lastIndexOf("---", markerIndex);
  const splitIndex = dividerIndex === -1 ? markerIndex : dividerIndex;
  const body = content.slice(0, splitIndex).trim();
  const block = content.slice(markerIndex).trim();
  const lines = block.split(/\r?\n/).map((line) => line.trimEnd());
  const sources: TrustedSource[] = [];
  let confidence: number | null = null;
  let warning: string | null = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("> 来源覆盖率：")) {
      confidence = parsePercent(trimmed.replace("> 来源覆盖率：", ""));
      continue;
    }
    if (trimmed.startsWith("> 置信提示：")) {
      warning = trimmed.replace("> 置信提示：", "").trim();
      continue;
    }

    const sourceMatch = trimmed.match(
      /^- \[(\d+)\] (.+?)（相关度\s+([0-9.]+)%(?:[，,]\s*片段\s+(.+?))?）$/
    );
    if (sourceMatch) {
      sources.push({
        index: Number(sourceMatch[1]),
        label: sourceMatch[2],
        score: Number(sourceMatch[3]) / 100,
        chunkId: sourceMatch[4],
      });
      continue;
    }

    if (trimmed.startsWith(">") && sources.length > 0) {
      sources[sources.length - 1].snippet = trimmed.replace(/^>\s*/, "");
    }
  }

  return { content: body, confidence, warning, sources };
}

function normalizeStructuredSources(sources?: ResourceSource[]): TrustedSource[] {
  if (!sources?.length) return [];
  return sources.map((source, index) => ({
    index: index + 1,
    label: formatSourceLabel(source),
    score: typeof source.score === "number" ? source.score : null,
    chunkId: source.chunk_id,
    snippet: source.snippet,
    sourceName: source.source_name,
  }));
}

function formatSourceLabel(source: ResourceSource): string {
  const location = [source.chapter, source.section].filter(Boolean).join(" > ");
  const title = source.title || source.source_name || source.chunk_id || "未知来源";
  return location ? `${location} — ${title}` : title;
}

function parsePercent(value: string): number | null {
  const numeric = Number(value.replace("%", "").trim());
  return Number.isFinite(numeric) ? numeric / 100 : null;
}

function formatPercent(value: number | null): string | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return `${Math.round(value * 100)}%`;
}

function buildWikiSourceHref(source: TrustedSource): string {
  const query = source.chunkId || source.label;
  return `/wiki?query=${encodeURIComponent(query)}`;
}

function buildReportHref(resourceTitle: string, source: TrustedSource): string {
  const subject = encodeURIComponent("EduAgent 来源引用问题");
  const body = encodeURIComponent(
    `资源：${resourceTitle}\n来源：${source.label}\n片段：${source.snippet || source.chunkId || ""}`
  );
  return `mailto:?subject=${subject}&body=${body}`;
}

function TrustedCitationPanel({
  data,
  resourceTitle,
}: {
  data: TrustedCitationData;
  resourceTitle: string;
}) {
  if (data.sources.length === 0) return null;
  const confidenceLabel = formatPercent(data.confidence);

  return (
    <div className="mb-3 border-l-2 border-[var(--color-terracotta)] bg-[var(--color-parchment)]/70 px-3 py-2">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-warm-gray-800)]">
            <FileText className="h-3.5 w-3.5 text-[var(--color-terracotta)]" />
            可信引用
          </p>
          {confidenceLabel && (
            <p className="text-[11px] text-[var(--color-warm-gray-500)]">
              来源覆盖率 {confidenceLabel}
            </p>
          )}
        </div>
        <a
          href={buildReportHref(resourceTitle, data.sources[0])}
          className="inline-flex items-center gap-1 text-[11px] text-[var(--color-warm-gray-500)] underline-offset-2 hover:text-[var(--color-terracotta)] hover:underline"
        >
          <Flag className="h-3 w-3" />
          报告问题
        </a>
      </div>
      {data.warning && (
        <p className="mb-2 inline-flex items-start gap-1.5 text-xs leading-5 text-amber-700">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{data.warning}</span>
        </p>
      )}
      <div className="space-y-2">
        {data.sources.map((source) => (
          <div
            key={`${source.index}-${source.chunkId || source.label}`}
            className="border-t border-[var(--color-warm-gray-200)] pt-2 first:border-t-0 first:pt-0"
          >
            <div className="flex flex-wrap items-center gap-2">
              <a
                href={buildWikiSourceHref(source)}
                className="inline-flex items-center gap-1 break-words text-xs font-medium text-[var(--color-warm-gray-700)] underline-offset-2 hover:text-[var(--color-terracotta)] hover:underline"
              >
                <ExternalLink className="h-3 w-3 shrink-0" />
                [{source.index}] {source.label}
              </a>
              {formatPercent(source.score) && (
                <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                  相关度 {formatPercent(source.score)}
                </span>
              )}
            </div>
            {source.sourceName && (
              <p className="mt-1 text-[11px] text-[var(--color-warm-gray-400)]">
                {source.sourceName}
              </p>
            )}
            {source.snippet && (
              <p className="mt-1 break-words text-xs leading-5 text-[var(--color-warm-gray-600)]">
                {source.snippet}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResourceCard({ resource: initialResource, sessionId }: ResourceCardProps) {
  const [resource, setResource] = useState(initialResource);
  const [expanded, setExpanded] = useState(true);
  const [speechState, setSpeechState] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isFavorite, setIsFavorite] = useState(Boolean(resource.is_favorite));
  const [actionError, setActionError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<"markdown" | "pptx" | null>(null);
  const [exportingAnimation, setExportingAnimation] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [favoriteSaving, setFavoriteSaving] = useState(false);
  const [shared, setShared] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const typeLabel = RESOURCE_TYPE_LABELS[resource.resource_type] ?? resource.resource_type;
  const colorClass = RESOURCE_TYPE_COLORS[resource.resource_type] ?? "bg-[var(--color-terracotta)]";
  const ResourceIcon =
    RESOURCE_TYPE_ICONS[resource.resource_type as keyof typeof RESOURCE_TYPE_ICONS] ??
    BookOpenText;
  const citationData = useMemo(() => buildTrustedCitationData(resource), [resource]);
  const displayContent = citationData.content;

  const isInteractiveQuiz = useMemo(() => {
    if (resource.resource_type !== "quiz") return false;
    try {
      const parsed = JSON.parse(displayContent);
      return parsed?.questions && Array.isArray(parsed.questions);
    } catch {
      return false;
    }
  }, [resource.resource_type, displayContent]);

  const isMindmap = resource.resource_type === "mindmap";
  const isPPT = resource.resource_type === "ppt";
  const isAnimation = resource.resource_type === "animation";
  const isCode = resource.resource_type === "code";
  const isVideo = resource.resource_type === "video";

  const mermaidData = useMemo(() => {
    if (!isMindmap) return null;
    return extractMermaidBlocks(displayContent);
  }, [isMindmap, displayContent]);

  const isPptImages = useMemo(() => {
    if (!isPPT && resource.resource_type !== "ppt_images") return false;
    try {
      const parsed = JSON.parse(displayContent);
      return parsed?.type === "ppt_images" && Array.isArray(parsed.slides);
    } catch {
      return false;
    }
  }, [isPPT, resource.resource_type, displayContent]);

  useEffect(() => {
    setResource(initialResource);
    setIsFavorite(Boolean(initialResource.is_favorite));
  }, [initialResource]);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
    };
  }, []);

  async function handleSpeechClick() {
    if (!resource.id || speechState === "loading") return;
    setSpeechError(null);

    if (speechState === "playing" && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setSpeechState("idle");
      return;
    }

    setSpeechState("loading");
    try {
      const blob = await fetchResourceSpeech(resource.id);
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
      const audioUrl = URL.createObjectURL(blob);
      audioUrlRef.current = audioUrl;
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      audio.onended = () => setSpeechState("idle");
      audio.onerror = () => {
        setSpeechState("error");
        setSpeechError("语音播放失败");
      };
      await audio.play();
      setSpeechState("playing");
    } catch (error) {
      setSpeechState("error");
      setSpeechError(error instanceof Error ? error.message : "生成语音失败");
    }
  }

  async function handleRegenerateClick() {
    if (!resource.id || regenerating) return;
    setActionError(null);
    setRegenerating(true);
    try {
      const updated = await regenerateResource(resource.id);
      setResource({
        id: updated.id,
        resource_type: updated.resource_type,
        title: updated.title,
        content: updated.content,
        knowledge_point: updated.knowledge_point,
        agent_name: updated.agent_name,
        is_favorite: updated.is_favorite,
        confidence: updated.confidence,
        sources: updated.sources,
      });
      setIsFavorite(updated.is_favorite);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "重生成资源失败");
    } finally {
      setRegenerating(false);
    }
  }

  async function handleFavoriteClick() {
    if (!resource.id || favoriteSaving) return;
    setActionError(null);
    setFavoriteSaving(true);
    try {
      const updated = await setResourceFavorite(resource.id, !isFavorite);
      setIsFavorite(updated.is_favorite);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "更新收藏失败");
    } finally {
      setFavoriteSaving(false);
    }
  }

  async function handleExportClick(format: "markdown" | "pptx") {
    if (!resource.id || exportingFormat) return;
    setActionError(null);
    setExportingFormat(format);
    try {
      const blob =
        format === "pptx"
          ? await exportResourcePptx(resource.id)
          : await exportResourceMarkdown(resource.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `resource-${resource.id}.${format === "pptx" ? "pptx" : "md"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "导出资源失败");
    } finally {
      setExportingFormat(null);
    }
  }

  async function handleAnimationExportClick() {
    if (!resource.id || exportingAnimation) return;
    setActionError(null);
    setExportingAnimation(true);
    try {
      const asset = await createAnimationExportAsset(resource.id);
      const blob = await fetchAssetBlob(asset);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = asset.filename || `resource-${resource.id}-animation.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "生成动画导出包失败");
    } finally {
      setExportingAnimation(false);
    }
  }

  const speechLabel =
    speechState === "loading" ? "生成中" : speechState === "playing" ? "停止" : "朗读";

  return (
    <div className="overflow-hidden rounded-xl bg-[var(--color-ivory)] shadow-[var(--shadow-ring)]">
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--color-warm-gray-200)] px-4 py-3 transition-colors hover:bg-[var(--color-parchment)]">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex min-w-[220px] flex-1 items-center gap-2 text-left max-sm:min-w-0"
        >
          <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full ${colorClass} px-2.5 py-1 text-[11px] text-white`}>
            <ResourceIcon className="h-3.5 w-3.5" />
            {typeLabel}
          </span>
          <span className="line-clamp-1 flex-1 text-sm font-medium text-[var(--color-warm-gray-800)]">
            {resource.title}
          </span>
          <span className="shrink-0 text-xs text-[var(--color-warm-gray-400)]">
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </button>
        {!isVideo && (
          <button
            type="button"
            onClick={handleSpeechClick}
            disabled={!resource.id || speechState === "loading"}
            title={resource.id ? "使用讯飞 TTS 朗读资源" : "资源保存后可朗读"}
            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-[var(--color-warm-gray-200)] px-2.5 text-xs text-[var(--color-warm-gray-600)] hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {speechState === "playing" ? <Square className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
            {speechLabel}
          </button>
        )}
        <button
          type="button"
          onClick={handleFavoriteClick}
          disabled={!resource.id || favoriteSaving}
          title={isFavorite ? "取消收藏" : "收藏资源"}
          className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border px-2.5 text-xs hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50 ${
            isFavorite
              ? "border-[var(--color-terracotta)] text-[var(--color-terracotta)]"
              : "border-[var(--color-warm-gray-200)] text-[var(--color-warm-gray-600)]"
          }`}
        >
          <Star className={`h-3.5 w-3.5 ${isFavorite ? "fill-current" : ""}`} />
          <span className={isVideo ? "sr-only" : ""}>{isFavorite ? "已收藏" : "收藏"}</span>
        </button>
        {!isVideo && (
          <button
            type="button"
            onClick={() => handleExportClick("markdown")}
            disabled={!resource.id || exportingFormat !== null}
            title="导出 Markdown 文件"
            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-[var(--color-warm-gray-200)] px-2.5 text-xs text-[var(--color-warm-gray-600)] hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            {exportingFormat === "markdown" ? "导出中" : "MD"}
          </button>
        )}
        <button
          type="button"
          onClick={handleRegenerateClick}
          disabled={!resource.id || regenerating}
          title="只重生成当前资源"
          className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-[var(--color-warm-gray-200)] px-2.5 text-xs text-[var(--color-warm-gray-600)] hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${regenerating ? "animate-spin" : ""}`} />
          <span className={isVideo ? "sr-only" : ""}>{regenerating ? "生成中" : "重生成"}</span>
        </button>
        <button
          type="button"
          onClick={async () => {
            try {
              const url = `${window.location.origin}/resources?resource_id=${resource.id}`;
              await navigator.clipboard.writeText(url);
              setShared(true);
              setTimeout(() => setShared(false), 2000);
            } catch {
              // clipboard API not available
            }
          }}
          title="复制分享链接"
          className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-[var(--color-warm-gray-200)] px-2.5 text-xs text-[var(--color-warm-gray-600)] hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)]"
        >
          <Share2 className="h-3.5 w-3.5" />
          <span className={isVideo ? "sr-only" : ""}>{shared ? "已复制!" : "分享"}</span>
        </button>
        {isPPT && (
          <button
            type="button"
            onClick={() => handleExportClick("pptx")}
            disabled={!resource.id || exportingFormat !== null}
            title="导出 PPTX 文件"
            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-[var(--color-warm-gray-200)] px-2.5 text-xs text-[var(--color-warm-gray-600)] hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Presentation className="h-3.5 w-3.5" />
            {exportingFormat === "pptx" ? "导出中" : "PPTX"}
          </button>
        )}
        {isAnimation && (
          <button
            type="button"
            onClick={handleAnimationExportClick}
            disabled={!resource.id || exportingAnimation}
            title="导出动画 HTML、字幕和可选旁白音频"
            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-[var(--color-warm-gray-200)] px-2.5 text-xs text-[var(--color-warm-gray-600)] hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PackageOpen className="h-3.5 w-3.5" />
            {exportingAnimation ? "导出中" : "动画包"}
          </button>
        )}
      </div>
      {expanded && (
        <div className="px-4 py-3">
          {actionError && (
            <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
              {actionError}
            </div>
          )}
          {speechError && (
            <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
              {speechError}
            </div>
          )}
          <TrustedCitationPanel data={citationData} resourceTitle={resource.title} />
          {isInteractiveQuiz ? (
            <InteractiveQuiz content={displayContent} resourceId={resource.id} sessionId={sessionId} />
          ) : isPptImages ? (
            <PptImageGallery content={displayContent} />
          ) : isMindmap && mermaidData?.mermaidCode ? (
            <div>
              <MermaidRenderer code={mermaidData.mermaidCode} />
              {mermaidData.rest && (
                <div className="mt-3 border-t border-[var(--color-warm-gray-200)] pt-3">
                  <MarkdownRenderer content={mermaidData.rest} />
                </div>
              )}
            </div>
          ) : isPPT ? (
            <SlideViewer content={displayContent} />
          ) : isAnimation ? (
            <AnimationPlayer content={displayContent} title={resource.title} />
          ) : isCode ? (
            <CodeRunner content={displayContent} resourceId={resource.id} />
          ) : isVideo ? (
            <VideoResourceContent content={displayContent} />
          ) : (
            <MarkdownRenderer content={displayContent} />
          )}
        </div>
      )}
      {resource.knowledge_point && (
        <div className="border-t border-[var(--color-warm-gray-200)] px-4 py-2 text-xs text-[var(--color-warm-gray-400)]">
          知识点：{resource.knowledge_point}
        </div>
      )}
    </div>
  );
}
