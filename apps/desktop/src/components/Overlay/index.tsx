import { useGuideeStore } from "@/stores/guidee";
import { clsx } from "clsx";
import { useEffect, useRef, useState } from "react";
import { ChatPanel } from "@/components/Chat";
import { AgentStatus } from "@/components/AgentStatus";
import { Mic, Settings, Sparkles } from "lucide-react";
import { useScreen } from "@/hooks/useScreen";
import { useVoice } from "@/hooks/useVoice";
import { useAgent } from "@/hooks/useAgent";
import { streamChat } from "@/lib/stream";

const INACTIVITY_MS = 30_000;

export function Overlay() {
  const overlayVisible = useGuideeStore((s) => s.overlayVisible);
  const overlayExpanded = useGuideeStore((s) => s.overlayExpanded);
  const isListening = useGuideeStore((s) => s.isListening);
  const isThinking = useGuideeStore((s) => s.isThinking);
  const messages = useGuideeStore((s) => s.messages);
  const setOverlayExpanded = useGuideeStore((s) => s.setOverlayExpanded);
  const setOverlayVisible = useGuideeStore((s) => s.setOverlayVisible);
  const addMessage = useGuideeStore((s) => s.addMessage);
  const appendToMessage = useGuideeStore((s) => s.appendToMessage);
  const updateMessage = useGuideeStore((s) => s.updateMessage);
  const setThinking = useGuideeStore((s) => s.setThinking);

  const { captureScreen } = useScreen();
  const { startListening } = useVoice();
  const { handleUserRequest } = useAgent();
  const [input, setInput] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const inactivityRef = useRef<ReturnType<typeof setTimeout>>();

  const latestMessage = messages[messages.length - 1];

  const resetInactivity = () => {
    if (inactivityRef.current) clearTimeout(inactivityRef.current);
    inactivityRef.current = setTimeout(() => {
      if (!overlayExpanded) setOverlayVisible(false);
    }, INACTIVITY_MS);
  };

  useEffect(() => {
    resetInactivity();
    return () => {
      if (inactivityRef.current) clearTimeout(inactivityRef.current);
    };
  }, [overlayExpanded, messages.length]);

  const submit = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    addMessage({ role: "user", content: text });
    setThinking(true);
    resetInactivity();

    try {
      const screenshot = await captureScreen();
      const routed = await handleUserRequest(text, screenshot);

      if (routed?.type === "instant") {
        const assistantId = addMessage({
          role: "assistant",
          content: "",
          streaming: true,
        });
        await streamChat(
          { transcript: text, screenshot_b64: screenshot },
          (token) => appendToMessage(assistantId, token),
          () =>
            updateMessage(assistantId, { streaming: false }),
          (err) =>
            updateMessage(assistantId, {
              content: `Error: ${err.message}`,
              streaming: false,
            })
        );
      }
    } finally {
      setThinking(false);
    }
  };

  if (!overlayVisible) return null;

  return (
    <div
      className={clsx(
        "fixed bottom-6 right-6 z-[9999] flex flex-col items-end gap-2",
        "select-none"
      )}
      onMouseMove={resetInactivity}
    >
      {overlayExpanded && (
        <div className="w-[400px] rounded-2xl border border-guidee-border bg-guidee-bg/95 shadow-overlay backdrop-blur-xl">
          <ChatPanel
            messages={messages}
            input={input}
            onInputChange={setInput}
            onSubmit={submit}
            isThinking={isThinking}
          />
          <AgentStatus />
          {showSettings && (
            <div className="border-t border-guidee-border p-3">
              <SettingsPanel onClose={() => setShowSettings(false)} />
            </div>
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
          className="flex items-center gap-2 text-sm text-guidee-text"
        >
          <Sparkles className="h-4 w-4 text-guidee-accent" />
          <span className="max-w-[200px] truncate">
            {latestMessage?.content.slice(0, 60) || "Ask Guidee anything…"}
          </span>
        </button>

        <button
          type="button"
          onClick={startListening}
          className={clsx(
            "rounded-full p-2 transition-colors",
            isListening
              ? "bg-red-500/20 text-red-400"
              : "bg-guidee-accent/20 text-guidee-accent hover:bg-guidee-accent/30"
          )}
          title="Voice input"
        >
          <Mic className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={() => setShowSettings((s) => !s)}
          className="rounded-full p-2 text-guidee-muted hover:text-guidee-text"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function SettingsPanel({ onClose }: { onClose: () => void }) {
  return (
    <div className="text-sm text-guidee-muted">
      <p className="mb-2 font-medium text-guidee-text">Settings</p>
      <p>Hotkeys: ⌘⇧G toggle · ⌘⇧S capture · Esc dismiss</p>
      <button
        type="button"
        onClick={onClose}
        className="mt-2 text-guidee-accent hover:underline"
      >
        Close
      </button>
    </div>
  );
}
