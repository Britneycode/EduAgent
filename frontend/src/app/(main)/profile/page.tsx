"use client";

import { Suspense, useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  changePassword,
  fetchProfile,
  fetchProfileHistory,
  refreshToken,
  updateProfile,
} from "@/lib/api";
import { ProfileSummary } from "@/components/profile/ProfileSummary";
import { ProfileRadarChart } from "@/components/profile/ProfileRadarChart";
import { OnboardingWizard } from "@/components/profile/OnboardingWizard";
import type { Profile, ProfileHistoryItem } from "@/lib/types";

interface ProfileDraft {
  major: string;
  grade: string;
  cognitive_style: string;
  learning_goal: string;
  learning_pace: string;
  coding_level: string;
  weekly_hours: string;
  weak_points: string;
  interest_areas: string;
  knowledge_base: string;
}

function profileToDraft(profile: Profile): ProfileDraft {
  return {
    major: profile.major ?? "",
    grade: profile.grade ?? "",
    cognitive_style: profile.cognitive_style ?? "",
    learning_goal: profile.learning_goal ?? "",
    learning_pace: profile.learning_pace ?? "",
    coding_level: profile.coding_level ?? "",
    weekly_hours: profile.weekly_hours == null ? "" : String(profile.weekly_hours),
    weak_points: profile.weak_points.join("、"),
    interest_areas: profile.interest_areas.join("、"),
    knowledge_base: Object.entries(profile.knowledge_base)
      .map(([concept, level]) => `${concept}: ${String(level)}`)
      .join("\n"),
  };
}

function parseList(value: string): string[] {
  return value
    .split(/[、,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseKnowledgeBase(value: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const rawLine of value.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const parts = line.split(/[:：]/);
    const concept = parts[0]?.trim();
    if (!concept) continue;
    const level = parts.slice(1).join(":").trim() || "了解";
    result[concept] = level;
  }
  return result;
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

function ProfileContent() {
  const searchParams = useSearchParams();
  const sessionIdParam = searchParams.get("session_id");
  const sessionId = sessionIdParam ? parseInt(sessionIdParam, 10) : null;

  const [profile, setProfile] = useState<Profile | null>(null);
  const [historyReloadKey, setHistoryReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchProfile(sessionId ?? undefined);
      setProfile(data);
      setError(null);
    } catch {
      setError("获取学习画像失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  function handleProfileSaved(nextProfile: Profile) {
    setProfile(nextProfile);
    setHistoryReloadKey((key) => key + 1);
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl text-[var(--color-warm-gray-800)]">学习画像</h1>
        {sessionId && (
          <Link
            href={`/chat/${sessionId}`}
            className="text-sm text-[var(--color-terracotta)] hover:underline"
          >
            返回对话
          </Link>
        )}
      </div>

      {loading && (
        <div className="py-16 text-center">
          <p className="text-[var(--color-warm-gray-500)]">正在加载画像数据...</p>
        </div>
      )}

      {error && (
        <div className="py-16 text-center">
          <p className="mb-4 inline-block rounded-lg bg-[var(--color-parchment)] px-4 py-2 text-sm text-[var(--color-terracotta)] ring-1 ring-[var(--color-warm-gray-200)]">
            {error}
          </p>
          <div>
            <button
              onClick={() => {
                void loadProfile();
              }}
              className="rounded-xl bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)]"
            >
              重试
            </button>
          </div>
        </div>
      )}

      {!loading && !error && profile && !profile.major && (
        <div className="mb-8 rounded-2xl bg-amber-50 p-5 ring-1 ring-amber-200">
          <p className="mb-1 text-sm font-medium text-amber-800">🎯 完善学习画像，获得更精准的 AI 学习推荐</p>
          <p className="mb-4 text-xs text-amber-600">以下信息帮助 AI 更好地了解你的学习背景和偏好</p>
          <OnboardingWizard onComplete={() => loadProfile()} />
        </div>
      )}

      {!loading && !error && profile && profile.major && (
        <div className="space-y-6">
          <ProfileRadarChart profile={profile} />
          <ProfileEditor
            key={`${profile.user_id}-${profile.session_id ?? "global"}`}
            profile={profile}
            sessionId={sessionId ?? undefined}
            onSaved={handleProfileSaved}
          />
          <ProfileHistoryPanel reloadKey={historyReloadKey} />
          <SecurityPanel />
          <ProfileSummary profile={profile} />
        </div>
      )}

      {!loading && !error && profile && (
        <div className="mt-6 text-center">
          <p className="text-xs text-[var(--color-warm-gray-400)]">
            画像数据会随你的对话自动更新，维度越完整，学习资料越个性化。
          </p>
        </div>
      )}
    </div>
  );
}

const PROFILE_FIELD_LABELS: Record<string, string> = {
  major: "专业",
  grade: "年级",
  knowledge_base: "知识基础",
  cognitive_style: "认知风格",
  learning_goal: "学习目标",
  weak_points: "薄弱点",
  learning_pace: "学习节奏",
  interest_areas: "兴趣领域",
  coding_level: "编程水平",
  weekly_hours: "每周学时",
};

function ProfileHistoryPanel({ reloadKey }: { reloadKey: number }) {
  const [items, setItems] = useState<ProfileHistoryItem[]>([]);
  const [loadedKey, setLoadedKey] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loading = loadedKey !== reloadKey;
  const visibleError = loading ? null : error;

  useEffect(() => {
    let cancelled = false;
    fetchProfileHistory(12)
      .then((history) => {
        if (!cancelled) {
          setItems(history);
          setError(null);
          setLoadedKey(reloadKey);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setError("获取画像历史失败");
          setLoadedKey(reloadKey);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <section className="rounded-xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-medium text-[var(--color-warm-gray-800)]">
            画像变化轨迹
          </h2>
          <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
            记录 Agent 自动抽取和你手动编辑后的画像快照。
          </p>
        </div>
        <span className="rounded-full bg-[var(--color-parchment)] px-3 py-1 text-xs text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)]">
          {items.length} 条
        </span>
      </div>

      {loading ? (
        <p className="py-4 text-sm text-[var(--color-warm-gray-400)]">
          正在加载历史...
        </p>
      ) : visibleError ? (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
          {visibleError}
        </p>
      ) : items.length === 0 ? (
        <p className="py-4 text-sm text-[var(--color-warm-gray-400)]">
          暂无变化记录，画像更新后会在这里形成时间线。
        </p>
      ) : (
        <ol className="space-y-3">
          {items.map((item) => (
            <li
              key={item.id}
              className="rounded-lg bg-[var(--color-parchment)] px-4 py-3 ring-1 ring-[var(--color-warm-gray-100)]"
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-[var(--color-terracotta)] px-2 py-0.5 text-[11px] text-white">
                    {item.source === "manual" ? "手动编辑" : "Agent 更新"}
                  </span>
                  {item.session_id && (
                    <span className="text-[11px] text-[var(--color-warm-gray-400)]">
                      会话 #{item.session_id}
                    </span>
                  )}
                </div>
                <time className="text-[11px] text-[var(--color-warm-gray-400)]">
                  {new Date(item.created_at).toLocaleString("zh-CN")}
                </time>
              </div>
              <div className="mb-2 flex flex-wrap gap-1.5">
                {item.changed_fields.map((field) => (
                  <span
                    key={field}
                    className="rounded-full bg-[var(--color-ivory)] px-2 py-0.5 text-[11px] text-[var(--color-warm-gray-600)] ring-1 ring-[var(--color-warm-gray-200)]"
                  >
                    {PROFILE_FIELD_LABELS[field] ?? field}
                  </span>
                ))}
              </div>
              <p className="line-clamp-2 text-xs leading-6 text-[var(--color-warm-gray-500)]">
                {summarizeProfileHistory(item.profile_data)}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function summarizeProfileHistory(profile: Profile): string {
  const parts = [
    profile.major ? `专业 ${profile.major}` : "",
    profile.grade ? `年级 ${profile.grade}` : "",
    profile.learning_goal ? `目标：${profile.learning_goal}` : "",
    profile.weak_points.length > 0
      ? `薄弱点：${profile.weak_points.slice(0, 3).join("、")}`
      : "",
  ].filter(Boolean);
  return parts.join("；") || "已保存一版画像快照";
}

function SecurityPanel() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRefreshToken() {
    if (refreshing) return;
    setRefreshing(true);
    setMessage(null);
    setError(null);
    try {
      await refreshToken();
      setMessage("登录状态已刷新");
    } catch (err) {
      setError(err instanceof Error ? err.message : "刷新登录状态失败");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingPassword) return;

    if (newPassword.length < 6) {
      setError("新密码至少 6 位");
      setMessage(null);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("两次输入的新密码不一致");
      setMessage(null);
      return;
    }
    if (currentPassword === newPassword) {
      setError("新密码不能与当前密码相同");
      setMessage(null);
      return;
    }

    setSavingPassword(true);
    setMessage(null);
    setError(null);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("密码已修改");
    } catch (err) {
      setError(err instanceof Error ? err.message : "修改密码失败");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <section className="rounded-xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-base font-medium text-[var(--color-warm-gray-800)]">
          账号安全
        </h2>
        <button
          type="button"
          onClick={() => void handleRefreshToken()}
          disabled={refreshing}
          className="w-full rounded-lg bg-[var(--color-warm-gray-800)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-warm-gray-700)] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {refreshing ? "刷新中..." : "刷新登录状态"}
        </button>
      </div>

      <form onSubmit={(event) => void handleChangePassword(event)}>
        <div className="grid gap-3 md:grid-cols-3">
          <PasswordInput
            label="当前密码"
            value={currentPassword}
            onChange={setCurrentPassword}
            autoComplete="current-password"
          />
          <PasswordInput
            label="新密码"
            value={newPassword}
            onChange={setNewPassword}
            autoComplete="new-password"
          />
          <PasswordInput
            label="确认新密码"
            value={confirmPassword}
            onChange={setConfirmPassword}
            autoComplete="new-password"
          />
        </div>

        <div className="mt-4 flex justify-end">
          <button
            type="submit"
            disabled={savingPassword || !currentPassword || !newPassword || !confirmPassword}
            className="w-full rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {savingPassword ? "修改中..." : "修改密码"}
          </button>
        </div>
      </form>

      {(message || error) && (
        <p
          className={`mt-3 rounded-lg px-3 py-2 text-xs ${
            error
              ? "bg-red-50 text-red-700"
              : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-600)]"
          }`}
        >
          {error || message}
        </p>
      )}
    </section>
  );
}

function ProfileEditor({
  profile,
  sessionId,
  onSaved,
}: {
  profile: Profile;
  sessionId?: number;
  onSaved: (profile: Profile) => void;
}) {
  const [draft, setDraft] = useState<ProfileDraft>(() => profileToDraft(profile));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateDraft(field: keyof ProfileDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
    setMessage(null);
    setError(null);
  }

  async function handleSave() {
    if (saving) return;

    const weeklyText = draft.weekly_hours.trim();
    let weeklyHours: number | null = null;
    if (weeklyText) {
      const parsedWeeklyHours = Number(weeklyText);
      if (
        !Number.isInteger(parsedWeeklyHours) ||
        parsedWeeklyHours < 0 ||
        parsedWeeklyHours > 168
      ) {
        setError("每周学时需为 0-168 之间的整数");
        return;
      }
      weeklyHours = parsedWeeklyHours;
    }
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await updateProfile(
        {
          major: emptyToNull(draft.major),
          grade: emptyToNull(draft.grade),
          cognitive_style: emptyToNull(draft.cognitive_style),
          learning_goal: emptyToNull(draft.learning_goal),
          learning_pace: emptyToNull(draft.learning_pace),
          coding_level: emptyToNull(draft.coding_level),
          weekly_hours: weeklyHours,
          weak_points: parseList(draft.weak_points),
          interest_areas: parseList(draft.interest_areas),
          knowledge_base: parseKnowledgeBase(draft.knowledge_base),
        },
        sessionId
      );
      onSaved(updated);
      setDraft(profileToDraft(updated));
      setMessage("画像已保存");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存画像失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-xl bg-[var(--color-ivory)] p-5 ring-1 ring-[var(--color-warm-gray-200)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-medium text-[var(--color-warm-gray-800)]">
            编辑画像
          </h2>
          <p className="mt-1 text-xs text-[var(--color-warm-gray-400)]">
            主动修正后，后续资源生成会使用新的画像。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="rounded-lg bg-[var(--color-terracotta)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--color-terracotta-hover)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "保存中..." : "保存画像"}
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <ProfileInput label="专业" value={draft.major} onChange={(value) => updateDraft("major", value)} />
        <ProfileInput label="年级" value={draft.grade} onChange={(value) => updateDraft("grade", value)} />
        <ProfileInput label="认知风格" value={draft.cognitive_style} onChange={(value) => updateDraft("cognitive_style", value)} />
        <ProfileInput label="学习节奏" value={draft.learning_pace} onChange={(value) => updateDraft("learning_pace", value)} />
        <ProfileInput label="编程水平" value={draft.coding_level} onChange={(value) => updateDraft("coding_level", value)} />
        <ProfileInput label="每周学时" value={draft.weekly_hours} onChange={(value) => updateDraft("weekly_hours", value)} inputMode="numeric" />
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <ProfileTextarea label="学习目标" value={draft.learning_goal} onChange={(value) => updateDraft("learning_goal", value)} rows={3} />
        <ProfileTextarea label="知识基础" value={draft.knowledge_base} onChange={(value) => updateDraft("knowledge_base", value)} rows={3} placeholder="机器学习: 入门" />
        <ProfileTextarea label="薄弱点" value={draft.weak_points} onChange={(value) => updateDraft("weak_points", value)} rows={2} placeholder="反向传播、梯度下降" />
        <ProfileTextarea label="兴趣领域" value={draft.interest_areas} onChange={(value) => updateDraft("interest_areas", value)} rows={2} placeholder="NLP、计算机视觉" />
      </div>

      {(message || error) && (
        <p
          className={`mt-3 rounded-lg px-3 py-2 text-xs ${
            error
              ? "bg-red-50 text-red-700"
              : "bg-[var(--color-parchment)] text-[var(--color-warm-gray-600)]"
          }`}
        >
          {error || message}
        </p>
      )}
    </section>
  );
}

function PasswordInput({
  label,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: "current-password" | "new-password";
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-[var(--color-warm-gray-500)]">
        {label}
      </span>
      <input
        value={value}
        type="password"
        autoComplete={autoComplete}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)]"
      />
    </label>
  );
}

function ProfileInput({
  label,
  value,
  onChange,
  inputMode,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  inputMode?: "numeric";
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-[var(--color-warm-gray-500)]">
        {label}
      </span>
      <input
        value={value}
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] focus:outline-none focus:ring-[var(--color-terracotta)]"
      />
    </label>
  );
}

function ProfileTextarea({
  label,
  value,
  onChange,
  rows,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows: number;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-[var(--color-warm-gray-500)]">
        {label}
      </span>
      <textarea
        value={value}
        rows={rows}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="w-full resize-y rounded-lg bg-[var(--color-parchment)] px-3 py-2 text-sm leading-6 text-[var(--color-warm-gray-700)] ring-1 ring-[var(--color-warm-gray-200)] placeholder:text-[var(--color-warm-gray-400)] focus:outline-none focus:ring-[var(--color-terracotta)]"
      />
    </label>
  );
}

export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl px-4 py-8 text-center">
          <p className="text-[var(--color-warm-gray-500)]">正在加载...</p>
        </div>
      }
    >
      <ProfileContent />
    </Suspense>
  );
}
