import { useGuideeStore } from "@/stores/guidee";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { clsx } from "clsx";
import { useEffect, useRef, useState } from "react";
import { ChatPanel } from "@/components/Chat";
import { AgentStatus } from "@/components/AgentStatus";
import { Onboarding } from "@/components/Onboarding";
import { SettingsPanel } from "@/components/Settings";
import {
  ChevronDown,
  Maximize2,
  Mic,
  MicOff,
  Move,
  Pin,
  PinOff,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { useScreen } from "@/hooks/useScreen";
import { useVoice } from "@/hooks/useVoice";
import { useAgent } from "@/hooks/useAgent";
import { streamChat } from "@/lib/stream";

const INACTIVITY_MS = 30_000;

export function Overlay() {
  const overlayVisible = useGuideeStore((s) => s.overlayVisible);
  const overlayExpanded = useGuideeStore((s) => s.overlayExpanded);
  const overlayPinned = useGuideeStore((s) => s.overlayPinned);
  const onboardingComplete = useGuideeStore((s) => s.onboardingComplete);
  const isListening = useGuideeStore((s) => s.isListening);
  const isThinking = useGuideeStore((s) => s.isThinking);
  const messages = useGuideeStore((s) => s.messages);
  const autoCapture = useGuideeStore((s) => s.autoCapture);
  const confirmScreenCapture = useGuideeStore((s) => s.confirmScreenCapture);
  const screenCaptureSource = useGuideeStore((s) => s.screenCaptureSource);
  const selectedMonitorId = useGuideeStore((s) => s.selectedMonitorId);
  const voiceStatus = useGuideeStore((s) => s.voiceStatus);
  const voiceError = useGuideeStore((s) => s.voiceError);
  const setOverlayExpanded = useGuideeStore((s) => s.setOverlayExpanded);
  const setOverlayVisible = useGuideeStore((s) => s.setOverlayVisible);
  const setOverlayPinned = useGuideeStore((s) => s.setOverlayPinned);
  const addMessage = useGuideeStore((s) => s.addMessage);
  const clearMessages = useGuideeStore((s) => s.clearMessages);
  const appendToMessage = useGuideeStore((s) => s.appendToMessage);
  const updateMessage = useGuideeStore((s) => s.updateMessage);
  const setThinking = useGuideeStore((s) => s.setThinking);

  const { captureScreen } = useScreen();
  const { startListening, stopListening } = useVoice();
  const { handleUserRequest } = useAgent();
  const [input, setInput] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const inactivityRef = useRef<ReturnType<typeof setTimeout>>();

  const latestMessage = messages[messages.length - 1];

  const resetInactivity = () => {
    if (inactivityRef.current) clearTimeout(inactivityRef.current);
    if (overlayPinned) return;
    inactivityRef.current = setTimeout(() => {
      if (!overlayExpanded) setOverlayVisible(false);
    }, INACTIVITY_MS);
  };

  useEffect(() => {
    resetInactivity();
    return () => {
      if (inactivityRef.current) clearTimeout(inactivityRef.current);
    };
  }, [overlayExpanded, overlayPinned, messages.length]);

  const submit = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    addMessage({ role: "user", content: text });
    setThinking(true);
    resetInactivity();

    try {
      const shouldCapture =
        autoCapture &&
        (!confirmScreenCapture ||
          window.confirm("Share screen context with Guidee for this request?"));
      const screenshot = shouldCapture
        ? await captureScreen({
            source: screenCaptureSource,
            monitorId: selectedMonitorId,
          })
        : null;
      const routed = await handleUserRequest(text, screenshot);

      if (routed?.type === "instant") {
        const assistantId = addMessage({
          role: "assistant",
          content: "",
          streaming: true,
        });
        await streamChat(
          { transcript: text, screenshot },
          (token) => appendToMessage(assistantId, token),
          () => updateMessage(assistantId, { streaming: false }),
          (err) =>
            updateMessage(assistantId, {
              content: `Error: ${err.message}`,
              streaming: false,
            })
        );
      }
    } catch (error) {
      addMessage({
        role: "assistant",
        content: `Error: ${
          error instanceof Error ? error.message : "Unable to complete request."
        }`,
      });
    } finally {
      setThinking(false);
    }
  };

  if (!overlayVisible) return null;

  return (
    <div
      className={clsx(
        "fixed bottom-6 right-6 z-[9999] flex flex-col items-end gap-2 text-guidee-text",
        "select-none"
      )}
      onMouseMove={resetInactivity}
    >
      {overlayExpanded && (
        <div className="w-[420px] overflow-hidden rounded-lg border border-guidee-border bg-guidee-bg/95 shadow-overlay backdrop-blur-xl">
          <div className="flex items-center gap-1 border-b border-guidee-border bg-guidee-surface/70 px-2 py-2">
            <button
              type="button"
              onPointerDown={() => {
                void getCurrentWindow().startDragging().catch(() => undefined);
              }}
              className="rounded-md p-2 text-guidee-muted hover:bg-guidee-bg hover:text-guidee-text"
              title="Move overlay"
            >
              <Move className="h-4 w-4" />
            </button>
            <span className="min-w-0 flex-1 text-xs text-guidee-muted">
              {overlayPinned ? "Pinned overlay" : "Floating overlay"}
            </span>
            <button
              type="button"
              onClick={() => setOverlayPinned(!overlayPinned)}
              className="rounded-md p-2 text-guidee-muted hover:bg-guidee-bg hover:text-guidee-text"
              title={overlayPinned ? "Unpin overlay" : "Pin overlay"}
            >
              {overlayPinned ? (
                <PinOff className="h-4 w-4" />
              ) : (
                <Pin className="h-4 w-4" />
              )}
            </button>
            <button
              type="button"
              onClick={() => setOverlayExpanded(false)}
              className="rounded-md p-2 text-guidee-muted hover:bg-guidee-bg hover:text-guidee-text"
              title="Collapse overlay"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setOverlayVisible(false)}
              className="rounded-md p-2 text-guidee-muted hover:bg-guidee-bg hover:text-guidee-text"
              title="Dismiss overlay"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {!onboardingComplete ? (
            <Onboarding />
          ) : showSettings ? (
            <div className="p-4">
              <SettingsPanel onClose={() => setShowSettings(false)} />
            </div>
          ) : (
            <>
              <ChatPanel
                messages={messages}
                input={input}
                onInputChange={setInput}
                onSubmit={submit}
                onClear={clearMessages}
                isThinking={isThinking}
              />
              <AgentStatus />
            </>
          )}
        </div>
      )}

      <div
        className={clsx(
          "flex items-center gap-2 rounded-full border border-guidee-border",
          "bg-guidee-surface/95 px-3 py-2 shadow-overlay backdrop-blur-xl",
          "transition-all hover:border-guidee-accent/50"
        )}
      >
        <button
          type="button"
          onClick={() => setOverlayExpanded(!overlayExpanded)}
          className="flex min-w-0 items-center gap-2 text-sm text-guidee-text"
          title={overlayExpanded ? "Collapse Guidee" : "Open Guidee"}
        >
          {overlayExpanded ? (
            <Maximize2 className="h-4 w-4 text-guidee-accent" />
          ) : (
            <Sparkles className="h-4 w-4 text-guidee-accent" />
          )}
          <span className="max-w-[200px] truncate">
            {voiceError ||
              (voiceStatus === "recording"
                ? "Listening…"
                : voiceStatus === "waitingWake"
                  ? "Waiting for wake word…"
                : latestMessage?.content.slice(0, 60) || "Ask Guidee anything…")}
          </span>
        </button>

        <button
          type="button"
          onClick={() => void (isListening ? stopListening() : startListening())}
          className={clsx(
            "rounded-full p-2 transition-colors",
            isListening
              ? "bg-red-500/20 text-red-400"
              : "bg-guidee-accent/20 text-guidee-accent hover:bg-guidee-accent/30"
          )}
          title={isListening ? "Stop voice input" : "Start voice input"}
        >
          {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>

        <button
          type="button"
          onClick={() => {
            setOverlayExpanded(true);
            setShowSettings((s) => !s);
          }}
          className="rounded-full p-2 text-guidee-muted hover:text-guidee-text"
          title="Settings"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
