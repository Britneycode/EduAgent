const TOKEN_KEY = "eduagent_token";
const USER_ID_KEY = "eduagent_user_id";

export function saveToken(token: string, userId: number): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_ID_KEY, String(userId));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUserId(): number | null {
  if (typeof window === "undefined") return null;
  const id = localStorage.getItem(USER_ID_KEY);
  return id ? Number(id) : null;
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_ID_KEY);
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;
  try {
    const base64 = token.split(".")[1];
    const jsonStr = decodeURIComponent(
      Array.from(atob(base64), (c) =>
        "%" + c.charCodeAt(0).toString(16).padStart(2, "0")
      ).join("")
    );
    const payload = JSON.parse(jsonStr);
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}
