import { useGuideeStore } from "@/stores/guidee";
import { Loader2 } from "lucide-react";

export function AgentStatus() {
  const tasks = useGuideeStore((s) => s.agentTasks);
  const active = tasks.find(
    (t) => t.status === "running" || t.status === "pending"
  );

  if (!active) return null;

  const progress =
    active.stepsTotal && active.stepsDone
      ? Math.round((active.stepsDone / active.stepsTotal) * 100)
      : null;

  return (
    <div className="border-t border-guidee-border px-4 py-2">
      <div className="flex items-center gap-2 text-xs text-guidee-muted">
        <Loader2 className="h-3 w-3 animate-spin text-guidee-accent" />
        <span>
          {active.route} agent · {active.progressMessage ?? active.status}
        </span>
        {progress !== null && (
          <span className="ml-auto text-guidee-accent">{progress}%</span>
        )}
      </div>
      {progress !== null && (
        <div className="mt-1 h-1 overflow-hidden rounded-full bg-guidee-border">
          <div
            className="h-full bg-guidee-accent transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
