import type { Message } from "@/stores/guidee";
import { clsx } from "clsx";
import { Send } from "lucide-react";

interface ChatPanelProps {
  messages: Message[];
  input: string;
  onInputChange: (v: string) => void;
  onSubmit: () => void;
  isThinking: boolean;
}

export function ChatPanel({
  messages,
  input,
  onInputChange,
  onSubmit,
  isThinking,
}: ChatPanelProps) {
  return (
    <div className="flex max-h-[420px] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-guidee-muted">
            Ask about your screen or say &quot;guidee agent, …&quot; for tasks
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx(
              "rounded-xl px-3 py-2 text-sm leading-relaxed",
              msg.role === "user"
                ? "ml-8 bg-guidee-accent/20 text-guidee-text"
                : "mr-4 bg-guidee-surface text-guidee-text"
            )}
          >
            {msg.content}
            {msg.streaming && (
              <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-guidee-accent" />
            )}
          </div>
        ))}
        {isThinking && (
          <p className="text-sm text-guidee-muted">Thinking…</p>
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
          className="flex-1 rounded-lg border border-guidee-border bg-guidee-surface px-3 py-2 text-sm text-guidee-text placeholder:text-guidee-muted focus:border-guidee-accent focus:outline-none"
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
