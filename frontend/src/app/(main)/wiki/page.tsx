"use client";

import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";
import { KnowledgeGraphView } from "@/components/wiki/KnowledgeGraphView";
import {
  fetchWikiChapters,
  fetchWikiCourses,
  fetchWikiTree,
  searchWiki,
  uploadWikiDocument,
} from "@/lib/api";
import type {
  WikiChapter,
  WikiCourse,
  WikiConceptNode,
  WikiSearchResult,
} from "@/lib/types";

export default function WikiPage() {
  const [courses, setCourses] = useState<WikiCourse[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);
  const [chapters, setChapters] = useState<WikiChapter[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<string | null>(null);
  const [concepts, setConcepts] = useState<WikiConceptNode[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<WikiSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expandedConcept, setExpandedConcept] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const selectedCourse = courses.find((course) => course.id === selectedCourseId);

  const runSearch = useCallback(async (query: string) => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const data = await searchWiki(query, 5, selectedCourseId);
      setSearchResults(data.results || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, [selectedCourseId]);

  useEffect(() => {
    fetchWikiCourses()
      .then((items) => {
        setCourses(items);
        const defaultCourse = items.find((item) => item.is_default) || items[0];
        setSelectedCourseId(defaultCourse?.id ?? null);
      })
      .catch(() => {
        setCourses([]);
        setSelectedCourseId(null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedCourseId) {
      setChapters([]);
      setSelectedChapter(null);
      return;
    }
    setSelectedChapter(null);
    setExpandedConcept(null);
    fetchWikiChapters(selectedCourseId)
      .then(setChapters)
      .catch(() => setChapters([]));
  }, [selectedCourseId]);

  useEffect(() => {
    const initialQuery = new URLSearchParams(window.location.search).get("query");
    if (!initialQuery || !selectedCourseId) return;
    setSearchQuery(initialQuery);
    void runSearch(initialQuery);
  }, [runSearch, selectedCourseId]);

  useEffect(() => {
    if (!selectedChapter) {
      setConcepts([]);
      return;
    }
    setExpandedConcept(null);
    fetchWikiTree(selectedChapter, selectedCourseId)
      .then((data) => setConcepts(data.concepts || []))
      .catch(() => setConcepts([]));
  }, [selectedChapter, selectedCourseId]);

  const handleSearch = async () => {
    await runSearch(searchQuery);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setUploadFile(event.target.files?.[0] ?? null);
    setUploadMessage(null);
    setUploadError(null);
  };

  const handleUpload = async () => {
    if (!uploadFile || uploading) return;
    setUploading(true);
    setUploadMessage(null);
    setUploadError(null);
    try {
      const uploaded = await uploadWikiDocument(uploadFile, selectedCourseId);
      const query = uploaded.title;
      setSearchQuery(query);
      await runSearch(query);
      setUploadMessage(
        `已入库 ${uploaded.chunk_count} 个片段，可通过「${query}」检索。`
      );
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "上传资料失败");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-6 text-2xl text-[var(--color-warm-gray-800)] font-serif">
        知识库
      </h1>

      <section className="mb-6 rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
        <div className="grid gap-3 md:grid-cols-[280px_1fr] md:items-center">
          <label>
            <span className="mb-1 block text-xs text-[var(--color-warm-gray-500)]">
              课程
            </span>
            <select
              value={selectedCourseId || ""}
              onChange={(event) => setSelectedCourseId(event.target.value || null)}
              className="w-full rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            >
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
          </label>
          <div className="text-xs leading-6 text-[var(--color-warm-gray-500)]">
            <span className="font-medium text-[var(--color-warm-gray-700)]">
              {selectedCourse?.metadata_course_id || selectedCourse?.id || "未选择"}
            </span>
            {selectedCourse && (
              <span>
                {" "}
                · {selectedCourse.chapter_count} 章 · {selectedCourse.concept_count} 个知识点
              </span>
            )}
          </div>
        </div>
      </section>

      <section className="mb-6 rounded-xl bg-[var(--color-ivory)] p-4 ring-1 ring-[var(--color-warm-gray-200)]">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <label className="flex-1">
            <span className="mb-1 block text-xs text-[var(--color-warm-gray-500)]">
              上传课程资料
            </span>
            <input
              type="file"
              accept=".md,.markdown,.txt,.pdf,.pptx"
              onChange={handleFileChange}
              className="w-full rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] file:mr-3 file:rounded-md file:border-0 file:bg-[var(--color-warm-gray-800)] file:px-3 file:py-1.5 file:text-xs file:text-white focus:outline-none focus:ring-[var(--color-terracotta)]"
            />
          </label>
          <button
            type="button"
            onClick={() => void handleUpload()}
            disabled={!uploadFile || uploading}
            className="rounded-lg bg-[var(--color-warm-gray-800)] px-5 py-2.5 text-sm text-white transition-colors hover:bg-[var(--color-warm-gray-700)] disabled:cursor-not-allowed disabled:opacity-50 md:mt-5"
          >
            {uploading ? "入库中..." : "入库"}
          </button>
        </div>
        {(uploadMessage || uploadError) && (
          <p
            className={`mt-3 rounded-lg px-3 py-2 text-xs ${
              uploadError
                ? "bg-red-50 text-red-700"
                : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-600)]"
            }`}
          >
            {uploadError || uploadMessage}
          </p>
        )}
      </section>

      {/* 搜索 */}
      <div className="mb-8 flex gap-3">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="搜索知识点..."
          className="flex-1 rounded-xl bg-[var(--color-ivory)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="rounded-xl bg-[var(--color-terracotta)] px-6 py-3 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:opacity-50"
        >
          {searching ? "搜索中..." : "搜索"}
        </button>
      </div>

      {/* 搜索结果 */}
      {searchResults.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-lg text-[var(--color-warm-gray-700)] font-serif">
            搜索结果
          </h2>
          <div className="space-y-3">
            {searchResults.map((result) => (
              <div
                key={result.chunk_id}
                className="rounded-xl bg-[var(--color-ivory)] px-5 py-4 ring-1 ring-[var(--color-warm-gray-200)]"
              >
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-sm font-medium text-[var(--color-warm-gray-800)]">
                    {result.title}
                  </span>
                  <span className="rounded-full bg-[var(--color-parchment)] px-2 py-0.5 text-[11px] text-[var(--color-warm-gray-500)]">
                    {result.chapter} · {result.section}
                  </span>
                  <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                    相关度 {(result.score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-sm leading-7 text-[var(--color-warm-gray-600)]">
                  <MarkdownRenderer
                    content={
                      result.content.slice(0, 300) +
                      (result.content.length > 300 ? "..." : "")
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 章节列表 */}
      <h2 className="mb-4 text-lg text-[var(--color-warm-gray-700)] font-serif">
        课程章节
      </h2>
      {loading ? (
        <p className="py-8 text-center text-sm text-[var(--color-warm-gray-400)]">
          正在加载...
        </p>
      ) : chapters.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--color-warm-gray-400)]">
          暂无知识库数据
        </p>
      ) : (
        <div className="space-y-3">
          {chapters.map((ch) => (
            <div key={ch.id}>
              <button
                type="button"
                onClick={() =>
                  setSelectedChapter(selectedChapter === ch.id ? null : ch.id)
                }
                className="flex w-full items-center justify-between rounded-xl bg-[var(--color-ivory)] px-5 py-4 text-left ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)]"
              >
                <span className="text-sm font-medium text-[var(--color-warm-gray-800)]">
                  {ch.title}
                </span>
                <span className="text-xs text-[var(--color-warm-gray-400)]">
                  {selectedChapter === ch.id ? "收起" : "展开"}
                </span>
              </button>

              {selectedChapter === ch.id && concepts.length > 0 && (
                <div className="mt-3 space-y-3">
                  <KnowledgeGraphView
                    concepts={concepts}
                    selectedConcept={expandedConcept}
                    onSelectConcept={(concept) =>
                      setExpandedConcept(
                        expandedConcept === concept.name ? null : concept.name
                      )
                    }
                  />
                  <div className="ml-4 space-y-2">
                    {concepts.map((c) => (
                      <div
                        key={c.name}
                        className="rounded-lg bg-[var(--color-ivory)] px-4 py-3 ring-1 ring-[var(--color-warm-gray-100)]"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedConcept(
                              expandedConcept === c.name ? null : c.name
                            )
                          }
                          className="flex w-full items-center justify-between text-left"
                        >
                          <span className="text-sm text-[var(--color-warm-gray-700)]">
                            {c.name}
                          </span>
                          <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                            {c.section || c.chapter}
                          </span>
                        </button>
                        {expandedConcept === c.name && (
                          <div className="mt-2 border-t border-[var(--color-warm-gray-100)] pt-2">
                            {c.description && (
                              <p className="mb-2 text-xs leading-6 text-[var(--color-warm-gray-600)]">
                                {c.description}
                              </p>
                            )}
                            {c.prerequisites.length > 0 && (
                              <div className="flex flex-wrap gap-1.5">
                                <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                                  前置知识：
                                </span>
                                {c.prerequisites.map((p) => (
                                  <span
                                    key={p}
                                    className="rounded-full bg-[var(--color-parchment)] px-2 py-0.5 text-[11px] text-[var(--color-warm-gray-500)]"
                                  >
                                    {p}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
