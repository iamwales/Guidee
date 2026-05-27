import type { Message } from "@/stores/guidee";
import { clsx } from "clsx";
import { Loader2, Send, Trash2 } from "lucide-react";
import { useEffect, useRef } from "react";

interface ChatPanelProps {
  messages: Message[];
  input: string;
  onInputChange: (v: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  isThinking: boolean;
}

export function ChatPanel({
  messages,
  input,
  onInputChange,
  onSubmit,
  onClear,
  isThinking,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, messages[messages.length - 1]?.content, isThinking]);

  return (
    <div className="flex h-[430px] flex-col">
      <div className="flex items-center justify-between border-b border-guidee-border px-4 py-3">
        <div>
          <p className="text-sm font-medium text-guidee-text">Guidee</p>
          <p className="text-xs text-guidee-muted">Screen-aware assistant</p>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="rounded-md p-2 text-guidee-muted hover:bg-guidee-surface hover:text-guidee-text"
          title="Clear conversation"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="rounded-lg border border-dashed border-guidee-border p-4 text-sm text-guidee-muted">
            <p className="font-medium text-guidee-text">Ready when you are</p>
            <p className="mt-1">
              Ask about your screen, draft a response, or start a longer task.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx(
              "max-w-[86%] rounded-lg px-3 py-2 text-sm leading-relaxed",
              msg.role === "user"
                ? "ml-auto bg-guidee-accent/20 text-guidee-text"
                : "mr-auto bg-guidee-surface text-guidee-text"
            )}
          >
            <p className="whitespace-pre-wrap break-words">{msg.content}</p>
            <div className="mt-1 flex items-center justify-between gap-2 text-[10px] text-guidee-muted">
              <span>{new Date(msg.createdAt).toLocaleTimeString()}</span>
              {msg.streaming && (
                <span className="inline-flex items-center gap-1 text-guidee-accent">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  streaming
                </span>
              )}
            </div>
          </div>
        ))}
        {isThinking && (
          <div className="mr-auto inline-flex items-center gap-2 rounded-lg bg-guidee-surface px-3 py-2 text-sm text-guidee-muted">
            <Loader2 className="h-4 w-4 animate-spin text-guidee-accent" />
            Thinking
          </div>
        )}
      </div>

      <form
        className="flex gap-2 border-t border-guidee-border p-3"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Type a message…"
          className="min-w-0 flex-1 rounded-lg border border-guidee-border bg-guidee-surface px-3 py-2 text-sm text-guidee-text placeholder:text-guidee-muted focus:border-guidee-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={!input.trim() || isThinking}
          className="rounded-lg bg-guidee-accent p-2 text-white transition-colors hover:bg-guidee-accentHover disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
