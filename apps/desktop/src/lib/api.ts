import type { ScreenCapture } from "@/hooks/useScreen";

export function getApiUrl(): string {
  return (
    localStorage.getItem("guidee_api_url") ||
    import.meta.env.VITE_API_URL ||
    "http://localhost:8000"
  ).replace(/\/$/, "");
}

export function getAuthHeaders(): HeadersInit {
  const token =
    localStorage.getItem("guidee_token") ||
    localStorage.getItem("guidee_dev_token") ||
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
  confidence: number;
  source: "rules" | "claude" | "fallback";
}

export interface ScreenshotMetadata {
  source: ScreenCapture["source"];
  monitor_id?: number | null;
  monitor_name?: string | null;
  width: number;
  height: number;
  original_width: number;
  original_height: number;
  quality: number;
  byte_size: number;
}

export function screenshotPayload(capture?: ScreenCapture | null): {
  screenshot_b64: string | null;
  screenshot_media_type: ScreenCapture["mediaType"] | null;
  screenshot_metadata: ScreenshotMetadata | null;
} {
  if (!capture) {
    return {
      screenshot_b64: null,
      screenshot_media_type: null,
      screenshot_metadata: null,
    };
  }

  return {
    screenshot_b64: capture.imageB64,
    screenshot_media_type: capture.mediaType,
    screenshot_metadata: {
      source: capture.source,
      monitor_id: capture.monitorId ?? null,
      monitor_name: capture.monitorName ?? null,
      width: capture.width,
      height: capture.height,
      original_width: capture.originalWidth,
      original_height: capture.originalHeight,
      quality: capture.quality,
      byte_size: capture.byteSize,
    },
  };
}

export async function classifyIntent(
  transcript: string,
  screenshot?: ScreenCapture | null
): Promise<SupervisorResult> {
  const res = await fetch(`${getApiUrl()}/chat/supervisor`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      transcript,
      ...screenshotPayload(screenshot),
      history: [],
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function dispatchAgent(
  task: string,
  route?: string,
  screenshot?: ScreenCapture | null
): Promise<{ task_id: string; route: string }> {
  const res = await fetch(`${getApiUrl()}/agent/dispatch`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      task,
      route,
      ...screenshotPayload(screenshot),
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
