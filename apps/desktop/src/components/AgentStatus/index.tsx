import { useGuideeStore } from "@/stores/guidee";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

export function AgentStatus() {
  const tasks = useGuideeStore((s) => s.agentTasks);
  const active = tasks.find(
    (t) => t.status === "running" || t.status === "pending"
  );
  const recent = active ?? tasks[0];

  if (!recent) return null;

  const progress =
    recent.stepsTotal && recent.stepsDone
      ? Math.round((recent.stepsDone / recent.stepsTotal) * 100)
      : null;
  const isActive = recent.status === "running" || recent.status === "pending";

  return (
    <div className="border-t border-guidee-border px-4 py-2">
      <div className="flex items-center gap-2 text-xs text-guidee-muted">
        {isActive && <Loader2 className="h-3 w-3 animate-spin text-guidee-accent" />}
        {recent.status === "done" && (
          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
        )}
        {recent.status === "failed" && <XCircle className="h-3 w-3 text-red-400" />}
        <span className="min-w-0 flex-1 truncate">
          {recent.route} agent · {recent.progressMessage ?? recent.status}
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
