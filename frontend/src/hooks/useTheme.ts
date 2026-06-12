"use client";

import { useEffect, useState, useCallback } from "react";

function getInitialDarkMode(): boolean {
  if (typeof window === "undefined") return false;
  const stored = localStorage.getItem("theme");
  const prefers = window.matchMedia("(prefers-color-scheme: dark)").matches;
  return stored === "dark" || (!stored && prefers);
}

export function useTheme() {
  const [dark, setDark] = useState(getInitialDarkMode);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const toggle = useCallback(() => {
    setDark((prev) => {
      const next = !prev;
      localStorage.setItem("theme", next ? "dark" : "light");
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
  }, []);

  return { dark, toggle };
}
