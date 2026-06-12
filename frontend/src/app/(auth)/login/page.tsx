"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AlertCircle, ArrowRight, LockKeyhole, UserRound } from "lucide-react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("请填写用户名和密码");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await login(username.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl bg-[var(--color-ivory)] p-8 shadow-[var(--shadow-whisper)] ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-3xl font-medium text-[var(--color-terracotta)] font-serif">
          EduAgent
        </h1>
        <p className="text-sm text-[var(--color-warm-gray-500)]">
          登录你的学习账户
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="mb-1.5 block text-sm text-[var(--color-warm-gray-600)]">
            用户名
          </label>
          <div className="flex items-center gap-3 rounded-xl bg-[var(--color-parchment)] px-4 py-3 ring-1 ring-[var(--color-warm-gray-200)] focus-within:ring-[var(--color-terracotta)]">
            <UserRound className="h-4 w-4 shrink-0 text-[var(--color-warm-gray-400)]" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              className="min-w-0 flex-1 bg-transparent text-sm placeholder:text-[var(--color-warm-gray-400)] focus:outline-none"
              autoComplete="username"
            />
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-sm text-[var(--color-warm-gray-600)]">
            密码
          </label>
          <div className="flex items-center gap-3 rounded-xl bg-[var(--color-parchment)] px-4 py-3 ring-1 ring-[var(--color-warm-gray-200)] focus-within:ring-[var(--color-terracotta)]">
            <LockKeyhole className="h-4 w-4 shrink-0 text-[var(--color-warm-gray-400)]" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              className="min-w-0 flex-1 bg-transparent text-sm placeholder:text-[var(--color-warm-gray-400)] focus:outline-none"
              autoComplete="current-password"
            />
          </div>
        </div>

        {error && (
          <p className="flex items-center gap-2 rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--color-terracotta)] py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "正在登录..." : "登录"}
          {!loading && <ArrowRight className="h-4 w-4" />}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-[var(--color-warm-gray-500)]">
        还没有账户？{" "}
        <Link
          href="/register"
          className="text-[var(--color-terracotta)] hover:underline"
        >
          注册新账户
        </Link>
      </p>
    </div>
  );
}
