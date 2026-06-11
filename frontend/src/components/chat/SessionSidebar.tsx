"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  deleteSession,
  fetchSessions,
  renameSession,
  setSessionPinned,
} from "@/lib/api";
import type { ChatSession } from "@/lib/types";

function formatSessionTime(value: string): string {
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function PencilIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M13.75 3.75L16.25 6.25M5 15l2.4-.4L15.6 6.4a1.06 1.06 0 000-1.5l-.5-.5a1.06 1.06 0 00-1.5 0L5.4 12.6 5 15z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M12.9 3.75l3.35 3.35-2.1 1.2v3.2l1.3 1.3H9.8l-3.55 3.45v-3.45H4.55l1.3-1.3V8.3l7.05-4.55z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ShareIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M12.5 5.2L7.7 8m4.8 4L7.7 9.2M13.75 4a1.75 1.75 0 110 3.5 1.75 1.75 0 010-3.5zM6.25 7.25a1.75 1.75 0 110 3.5 1.75 1.75 0 010-3.5zM13.75 12.5a1.75 1.75 0 110 3.5 1.75 1.75 0 010-3.5z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M5.8 6.1h8.4m-7.3 0v8m3.1-8v8m3.1-8v8M7.1 6.1V4.9c0-.5.4-.9.9-.9H12c.5 0 .9.4.9.9v1.2m-8 0l.6 9c0 .6.5 1 1.1 1h6.8c.6 0 1.1-.4 1.1-1l.6-9"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

type Notice = {
  type: "success" | "error";
  message: string;
};

interface SessionSidebarProps {
  mobile?: boolean;
  onNavigate?: () => void;
}

export function SessionSidebar({ mobile = false, onNavigate }: SessionSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [openMenuSessionId, setOpenMenuSessionId] = useState<number | null>(null);
  const [pendingDeleteSession, setPendingDeleteSession] =
    useState<ChatSession | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const [pendingRenameSession, setPendingRenameSession] =
    useState<ChatSession | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renamingSessionId, setRenamingSessionId] = useState<number | null>(null);
  const [pinningSessionId, setPinningSessionId] = useState<number | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    let active = true;

    fetchSessions()
      .then((data) => {
        if (active) {
          setSessions(data);
        }
      })
      .catch((error) => {
        if (active) {
          setSessions([]);
          if (error instanceof Error && error.message.includes("401")) {
            setNotice({ type: "error", message: "登录状态已失效，请重新登录" });
          } else {
            setNotice({ type: "error", message: "加载会话失败，请稍后重试" });
          }
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [pathname]);

  useEffect(() => {
    setOpenMenuSessionId(null);
  }, [pathname]);

  useEffect(() => {
    if (!notice || notice.type !== "success") {
      return;
    }
    const timer = window.setTimeout(() => setNotice(null), 2500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const filteredSessions = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    return sessions.filter((session) =>
      keyword ? (session.title || "").toLowerCase().includes(keyword) : true
    );
  }, [searchQuery, sessions]);

  const pinnedSessions = useMemo(
    () => filteredSessions.filter((session) => session.is_pinned),
    [filteredSessions]
  );
  const recentSessions = useMemo(
    () => filteredSessions.filter((session) => !session.is_pinned),
    [filteredSessions]
  );

  const sortSessions = (list: ChatSession[]) => {
    const copy = [...list];
    copy.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) {
        return a.is_pinned ? -1 : 1;
      }
      if (a.is_pinned && b.is_pinned) {
        const aPinnedAt = a.pinned_at ? new Date(a.pinned_at).getTime() : 0;
        const bPinnedAt = b.pinned_at ? new Date(b.pinned_at).getTime() : 0;
        if (aPinnedAt !== bPinnedAt) {
          return bPinnedAt - aPinnedAt;
        }
      }
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
    return copy;
  };

  const replaceSession = (nextSession: ChatSession) => {
    setSessions((prev) =>
      sortSessions(
        prev.map((session) => (session.id === nextSession.id ? nextSession : session))
      )
    );
  };

  const handleCreateSession = () => {
    router.push("/chat");
    onNavigate?.();
  };

  const openRenameDialog = (session: ChatSession) => {
    setOpenMenuSessionId(null);
    setNotice(null);
    setRenameValue(session.title || "");
    setPendingRenameSession(session);
  };

  const closeRenameDialog = () => {
    if (renamingSessionId !== null) {
      return;
    }
    setPendingRenameSession(null);
    setRenameValue("");
  };

  const handleConfirmRename = async () => {
    if (!pendingRenameSession || renamingSessionId !== null) {
      return;
    }

    const title = renameValue.trim();
    if (!title) {
      setNotice({ type: "error", message: "对话名称不能为空" });
      return;
    }

    setRenamingSessionId(pendingRenameSession.id);
    setNotice(null);
    try {
      const updated = await renameSession(pendingRenameSession.id, title);
      replaceSession(updated);
      setPendingRenameSession(null);
      setRenameValue("");
      setNotice({ type: "success", message: "对话名称已更新" });
    } catch (error) {
      if (error instanceof Error && error.message.includes("401")) {
        setNotice({ type: "error", message: "登录状态已失效，请重新登录" });
      } else if (error instanceof Error && error.message.includes("会话不存在")) {
        setNotice({ type: "error", message: "会话不存在或已被删除，请刷新后重试" });
      } else {
        setNotice({ type: "error", message: "重命名失败，请稍后重试" });
      }
    } finally {
      setRenamingSessionId(null);
    }
  };

  const openDeleteConfirm = (session: ChatSession) => {
    if (deletingSessionId !== null || pathname === `/chat/${session.id}`) {
      return;
    }
    setOpenMenuSessionId(null);
    setNotice(null);
    setPendingDeleteSession(session);
  };

  const closeDeleteConfirm = () => {
    if (deletingSessionId !== null) {
      return;
    }
    setPendingDeleteSession(null);
  };

  const handleConfirmDelete = async () => {
    if (!pendingDeleteSession || deletingSessionId !== null) {
      return;
    }

    setDeletingSessionId(pendingDeleteSession.id);
    setNotice(null);
    try {
      await deleteSession(pendingDeleteSession.id);
      setSessions((prev) =>
        prev.filter((session) => session.id !== pendingDeleteSession.id)
      );
      setPendingDeleteSession(null);
      setOpenMenuSessionId(null);
      setNotice({ type: "success", message: "对话已删除" });
    } catch (error) {
      if (error instanceof Error && error.message.includes("401")) {
        setNotice({ type: "error", message: "登录状态已失效，请重新登录" });
      } else if (error instanceof Error && error.message.includes("会话不存在")) {
        setNotice({ type: "error", message: "会话不存在或已被删除，请刷新后重试" });
      } else {
        setNotice({ type: "error", message: "删除会话失败，请稍后重试" });
      }
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleTogglePinned = async (session: ChatSession) => {
    if (pinningSessionId !== null) {
      return;
    }

    setPinningSessionId(session.id);
    setOpenMenuSessionId(null);
    setNotice(null);
    try {
      const updated = await setSessionPinned(session.id, !session.is_pinned);
      replaceSession(updated);
      setNotice({
        type: "success",
        message: updated.is_pinned ? "已置顶对话" : "已取消置顶",
      });
    } catch (error) {
      if (error instanceof Error && error.message.includes("401")) {
        setNotice({ type: "error", message: "登录状态已失效，请重新登录" });
      } else if (error instanceof Error && error.message.includes("会话不存在")) {
        setNotice({ type: "error", message: "会话不存在或已被删除，请刷新后重试" });
      } else {
        setNotice({ type: "error", message: "置顶操作失败，请稍后重试" });
      }
    } finally {
      setPinningSessionId(null);
    }
  };

  const handleShareSession = async (session: ChatSession) => {
    const url = new URL(`/chat/${session.id}`, window.location.origin).toString();
    setOpenMenuSessionId(null);
    setNotice(null);

    try {
      if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
        await navigator.share({ title: session.title || "未命名对话", url });
        setNotice({ type: "success", message: "分享面板已打开" });
        return;
      }

      await navigator.clipboard.writeText(url);
      setNotice({ type: "success", message: "分享链接已复制" });
    } catch {
      try {
        await navigator.clipboard.writeText(url);
        setNotice({ type: "success", message: "分享链接已复制" });
      } catch {
        setNotice({ type: "error", message: "分享失败，请检查浏览器权限" });
      }
    }
  };

  const renderSessionItem = (session: ChatSession) => {
    const href = `/chat/${session.id}`;
    const isActive = pathname === href;
    const isMenuOpen = openMenuSessionId === session.id;
    const isDeleting = deletingSessionId === session.id;
    const isPinning = pinningSessionId === session.id;

    return (
      <div
        key={session.id}
        className={`rounded-xl transition-colors ${
          isActive
            ? "bg-[var(--color-parchment)] ring-1 ring-[var(--color-warm-gray-200)]"
            : "hover:bg-[var(--color-parchment)]"
        }`}
      >
        <div className="flex items-start gap-2 px-3 py-3">
          <Link href={href} onClick={onNavigate} className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <div
                    className={`truncate text-sm font-medium ${
                      isActive
                        ? "text-[var(--color-terracotta)]"
                        : "text-[var(--color-warm-gray-700)]"
                    }`}
                  >
                    {session.title || "未命名对话"}
                  </div>
                  {session.is_pinned && (
                    <span className="shrink-0 rounded-full bg-[var(--color-warm-gray-200)] px-2 py-0.5 text-[10px] leading-none text-[var(--color-warm-gray-500)]">
                      置顶
                    </span>
                  )}
                </div>
                <div className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
                  {formatSessionTime(session.updated_at)}
                </div>
              </div>
              {isActive && (
                <span className="mt-0.5 shrink-0 whitespace-nowrap rounded-full bg-[var(--color-terracotta)] px-2 py-0.5 text-[10px] leading-none text-white">
                  当前
                </span>
              )}
            </div>
          </Link>

          {!isActive && (
            <div className="relative shrink-0">
              <button
                type="button"
                aria-label="更多操作"
                onClick={() => {
                  setNotice(null);
                  setOpenMenuSessionId((prev) => (prev === session.id ? null : session.id));
                }}
                disabled={
                  deletingSessionId !== null ||
                  renamingSessionId !== null ||
                  pinningSessionId !== null
                }
                className="rounded-lg px-2 py-1 text-sm text-[var(--color-warm-gray-400)] transition-colors hover:bg-[var(--color-parchment)] hover:text-[var(--color-warm-gray-700)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                ⋯
              </button>

              {isMenuOpen && (
                <div className="absolute right-0 top-9 z-10 min-w-36 rounded-2xl bg-[var(--color-ivory)] p-1.5 ring-1 ring-[var(--color-warm-gray-200)]">
                  <button
                    type="button"
                    onClick={() => openRenameDialog(session)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-[var(--color-warm-gray-700)] transition-colors hover:bg-[var(--color-parchment)]"
                  >
                    <PencilIcon />
                    <span>重命名</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTogglePinned(session)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-[var(--color-warm-gray-700)] transition-colors hover:bg-[var(--color-parchment)]"
                  >
                    <PinIcon />
                    <span>{session.is_pinned ? "取消置顶" : "置顶"}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleShareSession(session)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-[var(--color-warm-gray-700)] transition-colors hover:bg-[var(--color-parchment)]"
                  >
                    <ShareIcon />
                    <span>分享</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => openDeleteConfirm(session)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-[var(--color-terracotta)] transition-colors hover:bg-[var(--color-parchment)]"
                  >
                    <TrashIcon />
                    <span>删除</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {(isDeleting || isPinning) && (
          <div className="px-3 pb-3 text-xs text-[var(--color-warm-gray-400)]">
            {isDeleting ? "正在删除..." : "正在更新..."}
          </div>
        )}
      </div>
    );
  };

  const hasAnySessions = pinnedSessions.length > 0 || recentSessions.length > 0;

  return (
    <>
      <aside
        className={
          mobile
            ? "flex h-full w-full flex-col bg-[var(--color-ivory)]"
            : "hidden w-72 shrink-0 border-r border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)] md:flex md:flex-col"
        }
      >
        <div className="border-b border-[var(--color-warm-gray-200)] px-4 py-4">
          <button
            type="button"
            onClick={handleCreateSession}
            className="w-full rounded-xl bg-[var(--color-terracotta)] px-4 py-2.5 text-sm text-white transition-colors hover:bg-[var(--color-terracotta)]/90"
          >
            新建对话
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-3 px-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索会话..."
              className="w-full rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-xs text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            />
          </div>

          {notice && (
            <p
              className={`mb-3 rounded-xl px-3 py-2 text-xs leading-5 ring-1 ${
                notice.type === "error"
                  ? "bg-[var(--color-parchment)] text-[var(--color-terracotta)] ring-[var(--color-warm-gray-200)]"
                  : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-700)] ring-[var(--color-warm-gray-200)]"
              }`}
            >
              {notice.message}
            </p>
          )}

          {loading ? (
            <p className="px-2 py-3 text-sm text-[var(--color-warm-gray-400)]">
              正在加载会话...
            </p>
          ) : !hasAnySessions ? (
            <p className="px-2 py-3 text-sm leading-6 text-[var(--color-warm-gray-400)]">
              暂无会话，点击上方按钮开始学习。
            </p>
          ) : (
            <div className="space-y-5">
              {pinnedSessions.length > 0 && (
                <section>
                  <div className="mb-3 px-2 text-[11px] tracking-[0.18em] text-[var(--color-warm-gray-400)] uppercase">
                    置顶会话
                  </div>
                  <nav className="space-y-2">{pinnedSessions.map(renderSessionItem)}</nav>
                </section>
              )}

              {recentSessions.length > 0 && (
                <section>
                  <div className="mb-3 px-2 text-[11px] tracking-[0.18em] text-[var(--color-warm-gray-400)] uppercase">
                    最近会话
                  </div>
                  <nav className="space-y-2">{recentSessions.map(renderSessionItem)}</nav>
                </section>
              )}
            </div>
          )}
        </div>
      </aside>

      {pendingRenameSession && (
        <div className="fixed inset-0 z-40 bg-black/20">
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="w-full max-w-sm rounded-2xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
              <h2 className="text-lg font-medium text-[var(--color-warm-gray-800)]">
                重命名对话
              </h2>
              <input
                type="text"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                placeholder="请输入对话名称"
                maxLength={255}
                className="mt-4 w-full rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
              />
              <div className="mt-5 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeRenameDialog}
                  disabled={renamingSessionId !== null}
                  className="rounded-xl px-4 py-2 text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => void handleConfirmRename()}
                  disabled={renamingSessionId !== null}
                  className="rounded-xl bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta)]/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {renamingSessionId !== null ? "正在保存..." : "保存"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {pendingDeleteSession && (
        <div className="fixed inset-0 z-40 bg-black/20">
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="w-full max-w-sm rounded-2xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
              <h2 className="text-lg font-medium text-[var(--color-warm-gray-800)]">
                删除对话
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--color-warm-gray-500)]">
                删除后不可恢复，确认删除这个对话吗？
              </p>
              <div className="mt-5 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeDeleteConfirm}
                  disabled={deletingSessionId !== null}
                  className="rounded-xl px-4 py-2 text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] transition-colors hover:bg-[var(--color-parchment)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => void handleConfirmDelete()}
                  disabled={deletingSessionId !== null}
                  className="rounded-xl bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta)]/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deletingSessionId !== null ? "正在删除..." : "删除"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
