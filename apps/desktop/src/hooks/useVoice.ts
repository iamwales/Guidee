import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { useCallback, useEffect } from "react";
import { useGuideeStore } from "@/stores/guidee";

export function useVoice() {
  const isListening = useGuideeStore((s) => s.isListening);
  const setListening = useGuideeStore((s) => s.setListening);

  useEffect(() => {
    const unlisten = listen<string>("transcription-ready", () => {
      setListening(false);
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, [setListening]);

  const startListening = useCallback(async () => {
    setListening(true);
    await invoke("start_listening");
  }, [setListening]);

  const stopListening = useCallback(async () => {
    await invoke("stop_listening");
    setListening(false);
  }, [setListening]);

  return { isListening, startListening, stopListening };
}
