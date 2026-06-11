import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EduAgent - 个性化学习助手",
  description: "基于多 Agent 的个性化学习系统",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[var(--color-parchment)] text-[var(--color-warm-gray-800)]">
        {children}
      </body>
    </html>
  );
}
