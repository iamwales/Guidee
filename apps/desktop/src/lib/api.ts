const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function getAuthHeaders(): HeadersInit {
  const token =
    localStorage.getItem("guidee_token") ||
    import.meta.env.VITE_DEV_TOKEN ||
    "dev:local-user";
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface SupervisorResult {
  route: "instant" | "browser" | "research" | "file" | "email" | "clarify";
  reasoning: string;
  clarify_question?: string | null;
  task?: string | null;
}

export async function classifyIntent(
  transcript: string,
  screenshotB64?: string | null
): Promise<SupervisorResult> {
  const res = await fetch(`${API_URL}/chat/supervisor`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      transcript,
      screenshot_b64: screenshotB64 ?? null,
      history: [],
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function dispatchAgent(
  task: string,
  route?: string,
  screenshotB64?: string | null
): Promise<{ task_id: string; route: string }> {
  const res = await fetch(`${API_URL}/agent/dispatch`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      task,
      route,
      screenshot_b64: screenshotB64 ?? null,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
