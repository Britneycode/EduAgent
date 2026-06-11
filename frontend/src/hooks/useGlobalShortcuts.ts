"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function useGlobalShortcuts() {
  const router = useRouter();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMod = e.ctrlKey || e.metaKey;

      // Ctrl/Cmd + N: 新建会话（导航到主页）
      if (isMod && e.key === "n") {
        e.preventDefault();
        router.push("/chat");
        return;
      }

      // Ctrl/Cmd + /: 聚焦输入框
      if (isMod && e.key === "/") {
        e.preventDefault();
        const textarea = document.querySelector<HTMLTextAreaElement>(
          "textarea"
        );
        textarea?.focus();
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router]);
}
