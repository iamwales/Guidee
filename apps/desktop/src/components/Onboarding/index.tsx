import { ensureNotificationPermission } from "@/lib/notifications";
import { useGuideeStore } from "@/stores/guidee";
import { Bell, Check, Mic, Monitor, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

export function Onboarding() {
  const setOnboardingComplete = useGuideeStore((s) => s.setOnboardingComplete);
  const setNotificationsEnabled = useGuideeStore(
    (s) => s.setNotificationsEnabled
  );
  const [notificationReady, setNotificationReady] = useState(false);

  const requestNotifications = async () => {
    const allowed = await ensureNotificationPermission();
    setNotificationsEnabled(allowed);
    setNotificationReady(allowed);
  };

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="text-sm font-semibold text-guidee-text">Set up Guidee</p>
        <p className="mt-1 text-xs text-guidee-muted">
          Review desktop permissions before using screen and voice features.
        </p>
      </div>

      <div className="grid gap-2">
        <PermissionRow
          icon={<Monitor className="h-4 w-4" />}
          title="Screen capture"
          detail="macOS may ask for Screen Recording the first time you ask about your screen."
        />
        <PermissionRow
          icon={<Mic className="h-4 w-4" />}
          title="Microphone"
          detail="Voice input uses the system microphone permission."
        />
        <PermissionRow
          icon={<Bell className="h-4 w-4" />}
          title="Notifications"
          detail="Agent completion and failure alerts can appear outside the overlay."
          action={
            <button
              type="button"
              onClick={requestNotifications}
              className="rounded-md border border-guidee-border px-2 py-1 text-xs text-guidee-text hover:bg-guidee-surface"
            >
              {notificationReady ? "Allowed" : "Enable"}
            </button>
          }
        />
      </div>

      <button
        type="button"
        onClick={() => setOnboardingComplete(true)}
        className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-guidee-accent px-3 py-2 text-sm font-medium text-white hover:bg-guidee-accentHover"
      >
        <ShieldCheck className="h-4 w-4" />
        Continue
      </button>
    </div>
  );
}

function PermissionRow({
  icon,
  title,
  detail,
  action,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-guidee-border bg-guidee-surface px-3 py-2">
      <span className="text-guidee-accent">{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm text-guidee-text">{title}</span>
        <span className="block text-xs text-guidee-muted">{detail}</span>
      </span>
      {action ?? <Check className="h-4 w-4 text-guidee-muted" />}
    </div>
  );
}
