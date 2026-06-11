let lastSessionId: number | null = null;

export function setLastSessionId(id: number): void {
  lastSessionId = id;
  try {
    sessionStorage.setItem("lastChatSessionId", String(id));
  } catch {
    // sessionStorage 不可用
  }
}

export function getLastSessionId(): number | null {
  if (lastSessionId !== null) return lastSessionId;
  try {
    const stored = sessionStorage.getItem("lastChatSessionId");
    if (stored) {
      const parsed = parseInt(stored, 10);
      if (!isNaN(parsed) && parsed > 0) {
        lastSessionId = parsed;
        return parsed;
      }
    }
  } catch {
    // sessionStorage 不可用
  }
  return null;
}

export function getChatHref(): string {
  const id = getLastSessionId();
  return id ? `/chat/${id}` : "/chat";
}
