"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    const id = window.setTimeout(() => {
      setChecked(true);
    }, 0);

    return () => window.clearTimeout(id);
  }, [router]);

  if (!checked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-parchment)]">
        <p className="text-sm text-[var(--color-warm-gray-400)]">正在验证身份...</p>
      </div>
    );
  }

  return <>{children}</>;
}
