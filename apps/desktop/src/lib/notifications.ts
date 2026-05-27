import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from "@tauri-apps/plugin-notification";

export async function ensureNotificationPermission(): Promise<boolean> {
  try {
    if (await isPermissionGranted()) return true;
    return (await requestPermission()) === "granted";
  } catch {
    return false;
  }
}

export async function notify(title: string, body: string): Promise<void> {
  if (localStorage.getItem("guidee_notifications_enabled") === "false") return;
  if (!(await ensureNotificationPermission())) return;
  sendNotification({ title, body });
}
