"use client";

import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  BrainCircuit,
  Command,
  HelpCircle,
  Library,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  PanelLeft,
  Repeat2,
  Route,
  Search,
  Sun,
  X,
} from "lucide-react";
import { SessionSidebar } from "@/components/chat/SessionSidebar";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { removeToken } from "@/lib/auth";
import { useGlobalShortcuts } from "@/hooks/useGlobalShortcuts";
import { useTheme } from "@/hooks/useTheme";
import { getChatHref } from "@/lib/lastSession";

const NAV_ITEMS = [
  { label: "对话", href: "chat", icon: MessageSquare },
  { label: "学习画像", href: "/profile", icon: BrainCircuit },
  { label: "资源中心", href: "/resources", icon: Library },
  { label: "知识库", href: "/wiki", icon: BookOpen },
  { label: "学习路径", href: "/path", icon: Route },
  { label: "今日复习", href: "/review", icon: Repeat2 },
  { label: "学习评估", href: "/analytics", icon: BarChart3 },
];

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function useFocusTrap<T extends HTMLElement>(
  open: boolean,
  onClose: () => void,
  initialFocusRef?: RefObject<HTMLElement | null>
) {
  const containerRef = useRef<T | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusFirst = () => {
      const container = containerRef.current;
      const initialTarget = initialFocusRef?.current;
      if (initialTarget) {
        initialTarget.focus();
        return;
      }
      const first = container?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      first?.focus();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const container = containerRef.current;
      if (!container) return;
      const focusable = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      ).filter((element) => element.offsetParent !== null);
      if (focusable.length === 0) {
        event.preventDefault();
        container.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.setTimeout(focusFirst, 0);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [initialFocusRef, open]);

  return containerRef;
}

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
  const mobileNavDialogRef = useFocusTrap<HTMLDivElement>(
    mobileNavOpen,
    () => setMobileNavOpen(false)
  );
  const mobileSessionsDialogRef = useFocusTrap<HTMLDivElement>(
    mobileSessionsOpen,
    () => setMobileSessionsOpen(false)
  );
  const searchDialogRef = useFocusTrap<HTMLDivElement>(
    searchOpen,
    () => setSearchOpen(false),
    searchInputRef
  );
  const shortcutsDialogRef = useFocusTrap<HTMLDivElement>(
    shortcutsOpen,
    () => setShortcutsOpen(false)
  );
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
  const isNavActive = (href: string) => {
    if (href === "chat") return pathname.startsWith("/chat");
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[var(--color-parchment)]">
      <header className="border-b border-[var(--color-warm-gray-200)] bg-[var(--color-ivory)]/95 shadow-[var(--shadow-whisper)] backdrop-blur-sm">
        <div className="flex max-w-full items-center justify-between gap-3 px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileSessionsOpen(true)}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-[var(--color-parchment)] px-3 text-sm text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] md:hidden"
              aria-label="打开会话列表"
            >
              <PanelLeft className="h-4 w-4" />
              会话
            </button>
            <Link
              href={chatHref}
              className="flex min-w-0 items-baseline gap-2 truncate font-serif text-xl font-medium text-[var(--color-terracotta)]"
            >
              <span>EduAgent</span>
              <span className="hidden text-[11px] font-sans uppercase tracking-[0.18em] text-[var(--color-warm-gray-400)] lg:inline">
                Learning Hub
              </span>
            </Link>
            <button
              onClick={() => setSearchOpen(true)}
              className="hidden h-9 items-center gap-2 rounded-lg bg-[var(--color-parchment)] px-3 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] hover:text-[var(--color-terracotta)] hover:shadow-[var(--shadow-ring-warm)] md:inline-flex"
              aria-label="搜索知识库"
            >
              <Search className="h-3.5 w-3.5" />
              搜索知识库
              <kbd className="rounded bg-[var(--color-sand)] px-1.5 py-0.5 text-[10px] text-[var(--color-warm-gray-500)]">
                Ctrl K
              </kbd>
            </button>
          </div>
          <nav className="hidden min-w-0 flex-wrap items-center justify-end gap-1 text-sm md:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.label}
                href={resolveHref(item.href)}
                className={`inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-[13px] ${
                  isNavActive(item.href)
                    ? "bg-[var(--color-parchment)] text-[var(--color-terracotta)] shadow-[var(--shadow-ring)]"
                    : "text-[var(--color-warm-gray-600)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-terracotta)]"
                }`}
              >
                <item.icon className="h-3.5 w-3.5" />
                {item.label}
              </Link>
            ))}
            <button
              onClick={toggleTheme}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[var(--color-warm-gray-500)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-terracotta)]"
              title={dark ? "切换亮色模式" : "切换暗色模式"}
              aria-label={dark ? "切换亮色模式" : "切换暗色模式"}
            >
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              onClick={handleLogout}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-[13px] text-[var(--color-warm-gray-400)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-terracotta)]"
            >
              <LogOut className="h-3.5 w-3.5" />
              退出
            </button>
          </nav>
          <button
            type="button"
            onClick={() => setMobileNavOpen(true)}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-[var(--color-parchment)] px-3 text-sm text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)] md:hidden"
            aria-label="打开主菜单"
          >
            <Menu className="h-4 w-4" />
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
          <div
            ref={mobileNavDialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="主菜单"
            tabIndex={-1}
            className="absolute right-0 top-0 flex h-full w-72 max-w-[85vw] flex-col bg-[var(--color-ivory)] shadow-xl ring-1 ring-[var(--color-warm-gray-200)]"
          >
            <div className="flex items-center justify-between border-b border-[var(--color-warm-gray-200)] px-4 py-3">
              <span className="font-serif text-lg text-[var(--color-terracotta)]">
                EduAgent
              </span>
              <button
                type="button"
                onClick={() => setMobileNavOpen(false)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]"
                aria-label="关闭菜单"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <nav className="flex flex-col gap-1 p-3">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.label}
                  href={resolveHref(item.href)}
                  onClick={() => setMobileNavOpen(false)}
                  className={`inline-flex items-center gap-3 rounded-xl px-3 py-3 text-sm ${
                    isNavActive(item.href)
                      ? "bg-[var(--color-parchment)] text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]"
                      : "text-[var(--color-warm-gray-700)] hover:bg-[var(--color-parchment)]"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              ))}
              <button
                type="button"
                onClick={() => { toggleTheme(); setMobileNavOpen(false); }}
                className="inline-flex items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-[var(--color-warm-gray-700)] hover:bg-[var(--color-parchment)]"
              >
                {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                {dark ? "亮色模式" : "暗色模式"}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-[var(--color-terracotta)] hover:bg-[var(--color-parchment)]"
              >
                <LogOut className="h-4 w-4" />
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
          <div
            ref={mobileSessionsDialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="会话列表"
            tabIndex={-1}
            className="absolute left-0 top-0 h-full w-80 max-w-[88vw] overflow-hidden shadow-xl ring-1 ring-[var(--color-warm-gray-200)]"
          >
            <SessionSidebar
              mobile
              onNavigate={() => setMobileSessionsOpen(false)}
            />
          </div>
        </div>
      )}

      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 pt-[20vh]" onClick={() => setSearchOpen(false)}>
          <div
            ref={searchDialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="搜索知识库"
            tabIndex={-1}
            className="w-full max-w-lg rounded-2xl bg-[var(--color-ivory)] p-4 shadow-2xl ring-1 ring-[var(--color-warm-gray-200)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center gap-2 text-xs text-[var(--color-warm-gray-500)]">
              <Command className="h-4 w-4 text-[var(--color-terracotta)]" />
              搜索课程知识、来源片段和 Agent 生成内容
            </div>
            <div className="flex gap-3">
              <input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); if (e.key === "Escape") setSearchOpen(false); }}
                placeholder="搜索知识库中的知识点..."
                className="flex-1 rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
              />
              <button onClick={handleSearch} className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-terracotta)] px-5 py-3 text-sm text-white hover:bg-[var(--color-terracotta-hover)]">
                <Search className="h-4 w-4" />
                搜索
              </button>
            </div>
          </div>
        </div>
      )}

      {shortcutsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShortcutsOpen(false)}>
          <div
            ref={shortcutsDialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="快捷键"
            tabIndex={-1}
            className="w-full max-w-md rounded-2xl bg-[var(--color-ivory)] p-6 shadow-2xl ring-1 ring-[var(--color-warm-gray-200)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="inline-flex items-center gap-2 font-serif text-lg text-[var(--color-warm-gray-800)]">
                <HelpCircle className="h-4 w-4 text-[var(--color-terracotta)]" />
                快捷键
              </h3>
              <button onClick={() => setShortcutsOpen(false)} className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-warm-gray-400)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-terracotta)]" aria-label="关闭快捷键面板">
                <X className="h-4 w-4" />
              </button>
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
