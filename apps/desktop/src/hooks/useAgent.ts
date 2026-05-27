import { useCallback } from "react";
import type { ScreenCapture } from "@/hooks/useScreen";
import { classifyIntent, dispatchAgent } from "@/lib/api";
import { notify } from "@/lib/notifications";
import { streamAgentProgress } from "@/lib/stream";
import { useGuideeStore, type AgentTask } from "@/stores/guidee";

export function useAgent() {
  const addAgentTask = useGuideeStore((s) => s.addAgentTask);
  const updateAgentTask = useGuideeStore((s) => s.updateAgentTask);
  const addMessage = useGuideeStore((s) => s.addMessage);
  const notificationsEnabled = useGuideeStore((s) => s.notificationsEnabled);

  const handleUserRequest = useCallback(
    async (
      transcript: string,
      screenshot?: ScreenCapture | null
    ): Promise<{ type: "instant"; transcript: string } | void> => {
      const classification = await classifyIntent(transcript, screenshot);

      if (classification.route === "clarify") {
        addMessage({
          role: "assistant",
          content:
            classification.clarify_question ??
            "Could you clarify what you'd like me to do?",
        });
        return;
      }

      if (classification.route === "instant") {
        return { type: "instant", transcript };
      }

      const { task_id, route } = await dispatchAgent(
        classification.task ?? transcript,
        classification.route,
        screenshot
      );

      addAgentTask({
        id: task_id,
        route,
        status: "pending",
        taskInput: classification.task ?? transcript,
      });

      streamAgentProgress(task_id, (event) => {
        const status = (event.status as AgentTask["status"]) ?? "running";
        updateAgentTask(task_id, {
          status,
          stepsDone: event.steps_done as number | undefined,
          stepsTotal: event.steps_total as number | undefined,
          progressMessage: (event.message as string) ?? undefined,
          result: event.result as string | undefined,
        });

        if (event.type === "done" || event.status === "done") {
          if (notificationsEnabled) {
            void notify(
              "Guidee task completed",
              `${route} agent finished: ${classification.task ?? transcript}`
            );
          }
          addMessage({
            role: "assistant",
            content: String(event.result ?? "Task completed."),
          });
        }

        if (event.type === "error" || event.status === "failed") {
          if (notificationsEnabled) {
            void notify(
              "Guidee task failed",
              String(event.message ?? `${route} agent could not complete.`)
            );
          }
          addMessage({
            role: "assistant",
            content: `Agent failed: ${String(
              event.message ?? "Unable to complete the task."
            )}`,
          });
        }
      });

      addMessage({
        role: "assistant",
        content: `Running ${route} agent…`,
      });
    },
    [addAgentTask, updateAgentTask, addMessage, notificationsEnabled]
  );

  return { handleUserRequest };
}
