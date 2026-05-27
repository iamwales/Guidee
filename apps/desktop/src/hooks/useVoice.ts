import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { useCallback, useEffect } from "react";
import { useGuideeStore } from "@/stores/guidee";

interface VoiceStatusPayload {
  state: "idle" | "waitingWake" | "listening" | "recording" | "error";
  detail?: string;
}

export function useVoice() {
  const isListening = useGuideeStore((s) => s.isListening);
  const setListening = useGuideeStore((s) => s.setListening);
  const whisperModelPath = useGuideeStore((s) => s.whisperModelPath);
  const picovoiceAccessKey = useGuideeStore((s) => s.picovoiceAccessKey);
  const wakeWordModelPath = useGuideeStore((s) => s.wakeWordModelPath);
  const wakeWordKeywordPath = useGuideeStore((s) => s.wakeWordKeywordPath);
  const wakeWordEnabled = useGuideeStore((s) => s.wakeWordEnabled);
  const wakeWordSensitivity = useGuideeStore((s) => s.wakeWordSensitivity);
  const setVoiceStatus = useGuideeStore((s) => s.setVoiceStatus);
  const setVoiceError = useGuideeStore((s) => s.setVoiceError);

  useEffect(() => {
    const unsubs: Array<() => void> = [];
    listen<string>("transcription-ready", () => {
      setVoiceError(null);
    }).then((fn) => unsubs.push(fn));
    listen<VoiceStatusPayload>("voice-status", (event) => {
      setVoiceStatus(event.payload.state);
      setListening(event.payload.state !== "idle");
    }).then((fn) => unsubs.push(fn));
    listen<string>("voice-error", (event) => {
      setVoiceStatus("error");
      setVoiceError(event.payload);
    }).then((fn) => unsubs.push(fn));
    return () => {
      unsubs.forEach((fn) => fn());
    };
  }, [setListening, setVoiceError, setVoiceStatus]);

  const startListening = useCallback(async () => {
    setListening(true);
    setVoiceError(null);
    try {
      await invoke("start_listening", {
        options: {
          modelPath: whisperModelPath,
          picovoiceAccessKey,
          wakeWordModelPath,
          wakeWordKeywordPath,
          wakeWordEnabled,
          wakeWordSensitivity,
        },
      });
    } catch (error) {
      setListening(false);
      setVoiceStatus("error");
      setVoiceError(error instanceof Error ? error.message : String(error));
    }
  }, [
    setListening,
    setVoiceError,
    setVoiceStatus,
    picovoiceAccessKey,
    wakeWordKeywordPath,
    wakeWordModelPath,
    wakeWordEnabled,
    wakeWordSensitivity,
    whisperModelPath,
  ]);

  const stopListening = useCallback(async () => {
    await invoke("stop_listening");
    setListening(false);
    setVoiceStatus("idle");
  }, [setListening, setVoiceStatus]);

  return { isListening, startListening, stopListening };
}
