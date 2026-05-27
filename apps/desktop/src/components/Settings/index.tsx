import { ensureNotificationPermission } from "@/lib/notifications";
import { useGuideeStore } from "@/stores/guidee";
import { Bell, Camera, Check, KeyRound, Server, X } from "lucide-react";
import { useState } from "react";

interface SettingsPanelProps {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: SettingsPanelProps) {
  const apiUrl = useGuideeStore((s) => s.apiUrl);
  const devToken = useGuideeStore((s) => s.devToken);
  const autoCapture = useGuideeStore((s) => s.autoCapture);
  const notificationsEnabled = useGuideeStore((s) => s.notificationsEnabled);
  const setApiUrl = useGuideeStore((s) => s.setApiUrl);
  const setDevToken = useGuideeStore((s) => s.setDevToken);
  const setAutoCapture = useGuideeStore((s) => s.setAutoCapture);
  const setNotificationsEnabled = useGuideeStore(
    (s) => s.setNotificationsEnabled
  );

  const [draftApiUrl, setDraftApiUrl] = useState(apiUrl);
  const [draftToken, setDraftToken] = useState(devToken);
  const [saved, setSaved] = useState(false);

  const save = () => {
    setApiUrl(draftApiUrl);
    setDevToken(draftToken);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1400);
  };

  const toggleNotifications = async (enabled: boolean) => {
    if (!enabled) {
      setNotificationsEnabled(false);
      return;
    }
    setNotificationsEnabled(await ensureNotificationPermission());
  };

  return (
    <div className="space-y-4 text-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium text-guidee-text">Settings</p>
          <p className="text-xs text-guidee-muted">Runtime and overlay behavior</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-2 text-guidee-muted hover:bg-guidee-surface hover:text-guidee-text"
          title="Close settings"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <Server className="h-3.5 w-3.5" />
          API URL
        </span>
        <input
          value={draftApiUrl}
          onChange={(event) => setDraftApiUrl(event.target.value)}
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        />
      </label>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <KeyRound className="h-3.5 w-3.5" />
          Dev token
        </span>
        <input
          value={draftToken}
          onChange={(event) => setDraftToken(event.target.value)}
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        />
      </label>

      <label className="flex items-center justify-between rounded-md border border-guidee-border bg-guidee-surface px-3 py-2">
        <span className="flex items-center gap-2 text-guidee-text">
          <Camera className="h-4 w-4 text-guidee-accent" />
          Auto-capture screen context
        </span>
        <input
          type="checkbox"
          checked={autoCapture}
          onChange={(event) => setAutoCapture(event.target.checked)}
          className="h-4 w-4 accent-guidee-accent"
        />
      </label>

      <label className="flex items-center justify-between rounded-md border border-guidee-border bg-guidee-surface px-3 py-2">
        <span className="flex items-center gap-2 text-guidee-text">
          <Bell className="h-4 w-4 text-guidee-accent" />
          Agent completion notifications
        </span>
        <input
          type="checkbox"
          checked={notificationsEnabled}
          onChange={(event) => void toggleNotifications(event.target.checked)}
          className="h-4 w-4 accent-guidee-accent"
        />
      </label>

      <button
        type="button"
        onClick={save}
        className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-guidee-accent px-3 py-2 font-medium text-white hover:bg-guidee-accentHover"
      >
        <Check className="h-4 w-4" />
        {saved ? "Saved" : "Save settings"}
      </button>
    </div>
  );
}
