import { invoke } from "@tauri-apps/api/core";
import { useCallback, useState } from "react";

export function useScreen() {
  const [capturing, setCapturing] = useState(false);
  const [lastScreenshot, setLastScreenshot] = useState<string | null>(null);

  const captureScreen = useCallback(async () => {
    setCapturing(true);
    try {
      const b64 = await invoke<string>("capture_screen", {
        monitorId: null,
      });
      setLastScreenshot(b64);
      return b64;
    } finally {
      setCapturing(false);
    }
  }, []);

  return { captureScreen, capturing, lastScreenshot };
}
