import { invoke } from "@tauri-apps/api/core";
import { useCallback, useState } from "react";

export type CaptureSource = "selectedMonitor" | "focusedWindow" | "cursorMonitor";

export interface CaptureOptions {
  monitorId?: number | null;
  source?: CaptureSource;
  cursorX?: number | null;
  cursorY?: number | null;
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
}

export interface MonitorInfo {
  id: number;
  name?: string | null;
  friendlyName?: string | null;
  x?: number | null;
  y?: number | null;
  width: number;
  height: number;
  scaleFactor?: number | null;
  isPrimary?: boolean | null;
}

export interface ScreenCapture {
  imageB64: string;
  mediaType: "image/jpeg";
  source: CaptureSource;
  monitorId?: number | null;
  monitorName?: string | null;
  width: number;
  height: number;
  originalWidth: number;
  originalHeight: number;
  quality: number;
  byteSize: number;
}

export function useScreen() {
  const [capturing, setCapturing] = useState(false);
  const [monitors, setMonitors] = useState<MonitorInfo[]>([]);

  const captureScreen = useCallback(async (options?: CaptureOptions) => {
    setCapturing(true);
    try {
      return await invoke<ScreenCapture>("capture_screen", {
        options: options ?? null,
      });
    } finally {
      setCapturing(false);
    }
  }, []);

  const refreshMonitors = useCallback(async () => {
    const next = await invoke<MonitorInfo[]>("list_monitors");
    setMonitors(next);
    return next;
  }, []);

  return { captureScreen, capturing, monitors, refreshMonitors };
}
