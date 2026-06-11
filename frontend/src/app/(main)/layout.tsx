"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { SessionSidebar } from "@/components/chat/SessionSidebar";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { removeToken } from "@/lib/auth";
import { useGlobalShortcuts } from "@/hooks/useGlobalShortcuts";
import { useTheme } from "@/hooks/useTheme";
import { getChatHref } from "@/lib/lastSession";

const NAV_ITEMS = [
  { label: "对话", href: "chat" },
  { label: "学习画像", href: "/profile" },
  { label: "资源中心", href: "/resources" },
  { label: "知识库", href: "/wiki" },
  { label: "学习路径", href: "/path" },
  { label: "今日复习", href: "/review" },
  { label: "学习评估", href: "/analytics" },
];

function MainLayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [mobileSessionsOpen, setMobileSessionsOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const { dark, toggle: toggleTheme } = useTheme();
  const searchInputRef = useRef<HTMLInputElement>(null);
  useGlobalShortcuts();

  const chatHref = useMemo(() => {
    if (pathname.startsWith("/chat")) return pathname;
    return getChatHref();
  }, [pathname]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setSearchOpen(true); }
      if (e.key === "?" && e.shiftKey) { e.preventDefault(); setShortcutsOpen(true); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => { if (searchOpen) searchInputRef.current?.focus(); }, [searchOpen]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      router.push(`/wiki?query=${encodeURIComponent(searchQuery.trim())}`);
      setSearchOpen(false);
      setSearchQuery("");
    }
  };

  const handleLogout = () => {
    removeToken();
    router.replace("/login");
  };

  const resolveHref = (href: string) => (href === "chat" ? chatHref : href);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[var(--color-parchment)]">
      <header className="border-b border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)]/95 backdrop-blur-sm">
        <div className="flex max-w-full items-center justify-between px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileSessionsOpen(true)}
              className="rounded-lg px-3 py-2 text-sm text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] md:hidden"
            >
              会话
            </button>
            <Link
              href={chatHref}
              className="truncate text-xl font-medium text-[var(--color-terracotta)] font-serif"
            >
              EduAgent
            </Link>
            {/* 全局搜索 */}
            <button
              onClick={() => setSearchOpen(true)}
              className="hidden items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[var(--color-warm-gray-400)] ring-1 ring-[var(--color-warm-gray-200)] hover:text-[var(--color-terracotta)] md:inline-flex"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              搜索知识库
              <kbd className="text-[10px] opacity-50">Ctrl+K</kbd>
            </button>
          </div>
          <nav className="hidden flex-wrap items-center justify-end gap-x-4 gap-y-2 text-sm md:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.label}
                href={resolveHref(item.href)}
                className="text-[var(--color-warm-gray-600)] transition-colors hover:text-[var(--color-terracotta)]"
              >
                {item.label}
              </Link>
            ))}
            <button
              onClick={toggleTheme}
              className="text-lg transition-colors hover:scale-110"
              title={dark ? "切换亮色模式" : "切换暗色模式"}
            >
              {dark ? "☀️" : "🌙"}
            </button>
            <button
              onClick={handleLogout}
              className="text-[var(--color-warm-gray-400)] transition-colors hover:text-[var(--color-terracotta)]"
            >
              退出
            </button>
          </nav>
          <button
            type="button"
            onClick={() => setMobileNavOpen(true)}
            className="rounded-lg px-3 py-2 text-sm text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] md:hidden"
          >
            菜单
          </button>
        </div>
      </header>
      <div className="flex h-0 min-h-0 flex-1 overflow-hidden">
        <SessionSidebar />
        <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-[var(--color-parchment)]">
          <div className="min-h-0 flex-1 overflow-y-auto p-3 md:p-4">{children}</div>
        </main>
      </div>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 bg-black/25 md:hidden">
          <button
            type="button"
            aria-label="关闭菜单"
            className="absolute inset-0 h-full w-full"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="absolute right-0 top-0 flex h-full w-72 max-w-[85vw] flex-col bg-[var(--color-ivory)] shadow-xl ring-1 ring-[var(--color-warm-gray-200)]">
            <div className="flex items-center justify-between border-b border-[var(--color-warm-gray-200)] px-4 py-3">
              <span className="font-serif text-lg text-[var(--color-terracotta)]">
                EduAgent
              </span>
              <button
                type="button"
                onClick={() => setMobileNavOpen(false)}
                className="rounded-lg px-3 py-1.5 text-sm text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]"
              >
                关闭
              </button>
            </div>
            <nav className="flex flex-col gap-1 p-3">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.label}
                  href={resolveHref(item.href)}
                  onClick={() => setMobileNavOpen(false)}
                  className="rounded-xl px-3 py-3 text-sm text-[var(--color-warm-gray-700)] transition-colors hover:bg-[var(--color-parchment)]"
                >
                  {item.label}
                </Link>
              ))}
              <button
                type="button"
                onClick={() => { toggleTheme(); setMobileNavOpen(false); }}
                className="rounded-xl px-3 py-3 text-left text-sm text-[var(--color-warm-gray-700)] transition-colors hover:bg-[var(--color-parchment)]"
              >
                {dark ? "☀️ 亮色模式" : "🌙 暗色模式"}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-xl px-3 py-3 text-left text-sm text-[var(--color-terracotta)] transition-colors hover:bg-[var(--color-parchment)]"
              >
                退出
              </button>
            </nav>
          </div>
        </div>
      )}

      {mobileSessionsOpen && (
        <div className="fixed inset-0 z-50 bg-black/25 md:hidden">
          <button
            type="button"
            aria-label="关闭会话列表"
            className="absolute inset-0 h-full w-full"
            onClick={() => setMobileSessionsOpen(false)}
          />
          <div className="absolute left-0 top-0 h-full w-80 max-w-[88vw] overflow-hidden shadow-xl ring-1 ring-[var(--color-warm-gray-200)]">
            <SessionSidebar
              mobile
              onNavigate={() => setMobileSessionsOpen(false)}
            />
          </div>
        </div>
      )}

      {/* 全局搜索弹窗 */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 pt-[20vh]" onClick={() => setSearchOpen(false)}>
          <div className="w-full max-w-lg rounded-2xl bg-[var(--color-ivory)] p-4 shadow-2xl ring-1 ring-[var(--color-warm-gray-200)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex gap-3">
              <input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); if (e.key === "Escape") setSearchOpen(false); }}
                placeholder="搜索知识库中的知识点..."
                className="flex-1 rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
              />
              <button onClick={handleSearch} className="rounded-xl bg-[var(--color-terracotta)] px-5 py-3 text-sm text-white hover:bg-[var(--color-terracotta-hover)]">搜索</button>
            </div>
          </div>
        </div>
      )}

      {/* 快捷键面板 */}
      {shortcutsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShortcutsOpen(false)}>
          <div className="w-full max-w-md rounded-2xl bg-[var(--color-ivory)] p-6 shadow-2xl ring-1 ring-[var(--color-warm-gray-200)]" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-serif text-lg text-[var(--color-warm-gray-800)]">快捷键</h3>
              <button onClick={() => setShortcutsOpen(false)} className="text-[var(--color-warm-gray-400)] hover:text-[var(--color-terracotta)]">✕</button>
            </div>
            <div className="space-y-2 text-sm">
              {[
                ["Ctrl + K", "全局搜索知识库"],
                ["Shift + ?", "快捷键面板"],
                ["Enter", "发送消息"],
                ["Shift + Enter", "换行"],
                ["Esc", "停止生成 / 关闭弹窗"],
              ].map(([key, desc]) => (
                <div key={key} className="flex items-center justify-between rounded-lg bg-[var(--color-parchment)] px-3 py-2">
                  <span className="text-[var(--color-warm-gray-600)]">{desc}</span>
                  <kbd className="rounded bg-[var(--color-warm-gray-200)] px-2 py-0.5 text-xs text-[var(--color-warm-gray-500)]">{key}</kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <MainLayoutInner>{children}</MainLayoutInner>
    </AuthGuard>
  );
}
