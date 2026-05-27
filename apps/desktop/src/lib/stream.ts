import type { ScreenCapture } from "@/hooks/useScreen";
import {
  getApiUrl,
  getAuthHeaders,
  screenshotPayload,
  type ChatTurn,
} from "./api";

export interface ChatPayload {
  transcript: string;
  screenshot?: ScreenCapture | null;
  history?: ChatTurn[];
}

export async function streamChat(
  payload: ChatPayload,
  onToken: (token: string) => void,
  onDone?: () => void,
  onError?: (err: Error) => void
): Promise<void> {
  try {
    const res = await fetch(`${getApiUrl()}/chat/stream`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        transcript: payload.transcript,
        ...screenshotPayload(payload.screenshot),
        history: payload.history ?? [],
      }),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data && data !== "[DONE]") onToken(data);
        }
      }
    }
    onDone?.();
  } catch (e) {
    onError?.(e instanceof Error ? e : new Error(String(e)));
  }
}

export function streamAgentProgress(
  taskId: string,
  onEvent: (event: Record<string, unknown>) => void
): () => void {
  const token =
    localStorage.getItem("guidee_token") ||
    localStorage.getItem("guidee_dev_token") ||
    import.meta.env.VITE_DEV_TOKEN ||
    "dev:local-user";
  const url = `${getApiUrl()}/agent/${taskId}/stream?token=${encodeURIComponent(
    token
  )}`;
  const source = new EventSource(url, {
    // EventSource doesn't support custom headers — use fetch-based SSE in production
  } as EventSourceInit);

  // Fallback: poll status if EventSource auth fails
  source.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch {
      onEvent({ type: "progress", message: e.data });
    }
  };

  const poll = setInterval(async () => {
    const res = await fetch(`${getApiUrl()}/agent/${taskId}/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = await res.json();
      onEvent(data);
      if (data.status === "done" || data.status === "failed") {
        clearInterval(poll);
        source.close();
      }
    }
  }, 2000);

  return () => {
    source.close();
    clearInterval(poll);
  };
}
