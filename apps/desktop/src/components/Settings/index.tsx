import { ensureNotificationPermission } from "@/lib/notifications";
import { useGuideeStore } from "@/stores/guidee";
import { useScreen } from "@/hooks/useScreen";
import { Bell, Camera, Check, KeyRound, Mic, Monitor, Server, X } from "lucide-react";
import { useEffect, useState } from "react";

interface SettingsPanelProps {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: SettingsPanelProps) {
  const apiUrl = useGuideeStore((s) => s.apiUrl);
  const devToken = useGuideeStore((s) => s.devToken);
  const autoCapture = useGuideeStore((s) => s.autoCapture);
  const confirmScreenCapture = useGuideeStore((s) => s.confirmScreenCapture);
  const screenCaptureSource = useGuideeStore((s) => s.screenCaptureSource);
  const selectedMonitorId = useGuideeStore((s) => s.selectedMonitorId);
  const notificationsEnabled = useGuideeStore((s) => s.notificationsEnabled);
  const voiceError = useGuideeStore((s) => s.voiceError);
  const whisperModelPath = useGuideeStore((s) => s.whisperModelPath);
  const picovoiceAccessKey = useGuideeStore((s) => s.picovoiceAccessKey);
  const wakeWordModelPath = useGuideeStore((s) => s.wakeWordModelPath);
  const wakeWordKeywordPath = useGuideeStore((s) => s.wakeWordKeywordPath);
  const wakeWordEnabled = useGuideeStore((s) => s.wakeWordEnabled);
  const wakeWordSensitivity = useGuideeStore((s) => s.wakeWordSensitivity);
  const setApiUrl = useGuideeStore((s) => s.setApiUrl);
  const setDevToken = useGuideeStore((s) => s.setDevToken);
  const setAutoCapture = useGuideeStore((s) => s.setAutoCapture);
  const setConfirmScreenCapture = useGuideeStore(
    (s) => s.setConfirmScreenCapture
  );
  const setScreenCaptureSource = useGuideeStore(
    (s) => s.setScreenCaptureSource
  );
  const setSelectedMonitorId = useGuideeStore((s) => s.setSelectedMonitorId);
  const setNotificationsEnabled = useGuideeStore(
    (s) => s.setNotificationsEnabled
  );
  const setWhisperModelPath = useGuideeStore((s) => s.setWhisperModelPath);
  const setPicovoiceAccessKey = useGuideeStore((s) => s.setPicovoiceAccessKey);
  const setWakeWordModelPath = useGuideeStore((s) => s.setWakeWordModelPath);
  const setWakeWordKeywordPath = useGuideeStore(
    (s) => s.setWakeWordKeywordPath
  );
  const setWakeWordEnabled = useGuideeStore((s) => s.setWakeWordEnabled);
  const setWakeWordSensitivity = useGuideeStore(
    (s) => s.setWakeWordSensitivity
  );

  const [draftApiUrl, setDraftApiUrl] = useState(apiUrl);
  const [draftToken, setDraftToken] = useState(devToken);
  const [draftModelPath, setDraftModelPath] = useState(whisperModelPath);
  const [draftPicovoiceKey, setDraftPicovoiceKey] = useState(picovoiceAccessKey);
  const [draftWakeModelPath, setDraftWakeModelPath] =
    useState(wakeWordModelPath);
  const [draftWakeKeywordPath, setDraftWakeKeywordPath] =
    useState(wakeWordKeywordPath);
  const [saved, setSaved] = useState(false);
  const { monitors, refreshMonitors } = useScreen();

  useEffect(() => {
    void refreshMonitors().catch(() => undefined);
  }, [refreshMonitors]);

  const save = () => {
    setApiUrl(draftApiUrl);
    setDevToken(draftToken);
    setWhisperModelPath(draftModelPath);
    setPicovoiceAccessKey(draftPicovoiceKey);
    setWakeWordModelPath(draftWakeModelPath);
    setWakeWordKeywordPath(draftWakeKeywordPath);
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
          <Camera className="h-4 w-4 text-guidee-accent" />
          Confirm screen capture
        </span>
        <input
          type="checkbox"
          checked={confirmScreenCapture}
          onChange={(event) => setConfirmScreenCapture(event.target.checked)}
          className="h-4 w-4 accent-guidee-accent"
        />
      </label>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <Monitor className="h-3.5 w-3.5" />
          Capture source
        </span>
        <select
          value={screenCaptureSource}
          onChange={(event) =>
            setScreenCaptureSource(
              event.target.value as typeof screenCaptureSource
            )
          }
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        >
          <option value="selectedMonitor">Selected monitor</option>
          <option value="focusedWindow">Focused window</option>
          <option value="cursorMonitor">Cursor monitor</option>
        </select>
      </label>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <Monitor className="h-3.5 w-3.5" />
          Monitor
        </span>
        <select
          value={selectedMonitorId ?? ""}
          onChange={(event) =>
            setSelectedMonitorId(
              event.target.value ? Number(event.target.value) : null
            )
          }
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        >
          <option value="">Default monitor</option>
          {monitors.map((monitor) => (
            <option key={monitor.id} value={monitor.id}>
              {monitor.friendlyName || monitor.name || `Monitor ${monitor.id}`} (
              {monitor.width}x{monitor.height})
            </option>
          ))}
        </select>
      </label>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <KeyRound className="h-3.5 w-3.5" />
          Picovoice access key
        </span>
        <input
          type="password"
          value={draftPicovoiceKey}
          onChange={(event) => setDraftPicovoiceKey(event.target.value)}
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        />
      </label>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <Mic className="h-3.5 w-3.5" />
          Wake model path
        </span>
        <input
          placeholder="Bundled Porcupine model"
          value={draftWakeModelPath}
          onChange={(event) => setDraftWakeModelPath(event.target.value)}
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        />
      </label>

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <Mic className="h-3.5 w-3.5" />
          Wake keyword path
        </span>
        <input
          placeholder="Bundled Picovoice keyword"
          value={draftWakeKeywordPath}
          onChange={(event) => setDraftWakeKeywordPath(event.target.value)}
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
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

      <label className="block space-y-1">
        <span className="flex items-center gap-2 text-xs font-medium text-guidee-muted">
          <Mic className="h-3.5 w-3.5" />
          Whisper model path
        </span>
        <input
          value={draftModelPath}
          onChange={(event) => setDraftModelPath(event.target.value)}
          className="w-full rounded-md border border-guidee-border bg-guidee-surface px-3 py-2 text-guidee-text outline-none focus:border-guidee-accent"
        />
      </label>

      <label className="flex items-center justify-between rounded-md border border-guidee-border bg-guidee-surface px-3 py-2">
        <span className="flex items-center gap-2 text-guidee-text">
          <Mic className="h-4 w-4 text-guidee-accent" />
          Wake word detection
        </span>
        <input
          type="checkbox"
          checked={wakeWordEnabled}
          onChange={(event) => setWakeWordEnabled(event.target.checked)}
          className="h-4 w-4 accent-guidee-accent"
        />
      </label>

      <label className="block space-y-2 rounded-md border border-guidee-border bg-guidee-surface px-3 py-2">
        <span className="flex items-center justify-between text-guidee-text">
          <span>Wake sensitivity</span>
          <span className="text-xs text-guidee-muted">
            {wakeWordSensitivity.toFixed(2)}
          </span>
        </span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={wakeWordSensitivity}
          onChange={(event) =>
            setWakeWordSensitivity(Number(event.target.value))
          }
          className="w-full accent-guidee-accent"
        />
      </label>

      {voiceError ? (
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {voiceError}
        </div>
      ) : null}

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
