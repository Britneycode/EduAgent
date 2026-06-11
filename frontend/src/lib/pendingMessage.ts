let pendingMessage: string | null = null;
const STORAGE_KEY = "eduagent.pendingMessage";

function readStoredPendingMessage(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredPendingMessage(message: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, message);
  } catch {
    // 内存兜底仍可覆盖当前页面跳转。
  }
}

function clearStoredPendingMessage(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // 忽略浏览器存储不可用的场景。
  }
}

export function setPendingMessage(message: string): void {
  pendingMessage = message;
  writeStoredPendingMessage(message);
}

export function consumePendingMessage(): string | null {
  const msg = pendingMessage ?? readStoredPendingMessage();
  pendingMessage = null;
  clearStoredPendingMessage();
  return msg;
}
