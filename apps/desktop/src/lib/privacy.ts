const AUTH_TOKEN_KEY = "guidee_token";
const DEV_TOKEN_KEY = "guidee_dev_token";

export function getStoredAuthToken(): string | null {
  const legacyToken = localStorage.getItem(AUTH_TOKEN_KEY);
  if (legacyToken) {
    sessionStorage.setItem(AUTH_TOKEN_KEY, legacyToken);
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
  return sessionStorage.getItem(AUTH_TOKEN_KEY);
}

export function setStoredAuthToken(token: string | null): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  if (token) sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  else sessionStorage.removeItem(AUTH_TOKEN_KEY);
}

export function getBearerToken(): string {
  return (
    getStoredAuthToken() ||
    localStorage.getItem(DEV_TOKEN_KEY) ||
    import.meta.env.VITE_DEV_TOKEN ||
    (import.meta.env.DEV ? "dev:local-user" : "")
  );
}

export function redactForAudit(value: string): string {
  if (!value) return "";
  if (value.length <= 8) return "[redacted]";
  return `${value.slice(0, 4)}...[redacted:${value.length}]`;
}
