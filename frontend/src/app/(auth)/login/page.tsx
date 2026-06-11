"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
    <div className="rounded-2xl bg-[var(--color-ivory)] p-8 ring-1 ring-[var(--color-warm-gray-200)]">
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
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="请输入用户名"
            className="w-full rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            autoComplete="username"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm text-[var(--color-warm-gray-600)]">
            密码
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入密码"
            className="w-full rounded-xl bg-[var(--color-parchment)] px-4 py-3 text-sm ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
            autoComplete="current-password"
          />
        </div>

        {error && (
          <p className="rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-[var(--color-terracotta)] py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "正在登录..." : "登录"}
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
