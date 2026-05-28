import { create } from "zustand";
import { getStoredAuthToken, setStoredAuthToken } from "@/lib/privacy";

export type ScreenCaptureSource =
  | "selectedMonitor"
  | "focusedWindow"
  | "cursorMonitor";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  createdAt: number;
}

type NewMessage = Omit<Message, "id" | "createdAt"> & {
  createdAt?: number;
};

export interface AgentTask {
  id: string;
  route: string;
  status: "pending" | "running" | "done" | "failed" | "cancelled";
  taskInput: string;
  stepsTotal?: number;
  stepsDone?: number;
  progressMessage?: string;
  result?: string;
}

interface GuideeStore {
  messages: Message[];
  agentTasks: AgentTask[];
  isListening: boolean;
  isThinking: boolean;
  overlayVisible: boolean;
  overlayExpanded: boolean;
  overlayPinned: boolean;
  onboardingComplete: boolean;
  authToken: string | null;
  apiUrl: string;
  devToken: string;
  autoCapture: boolean;
  confirmScreenCapture: boolean;
  screenCaptureSource: ScreenCaptureSource;
  selectedMonitorId: number | null;
  notificationsEnabled: boolean;
  voiceStatus: "idle" | "waitingWake" | "listening" | "recording" | "error";
  voiceError: string | null;
  whisperModelPath: string;
  picovoiceAccessKey: string;
  wakeWordModelPath: string;
  wakeWordKeywordPath: string;
  wakeWordEnabled: boolean;
  wakeWordSensitivity: number;

  addMessage: (msg: NewMessage) => string;
  clearMessages: () => void;
  updateMessage: (id: string, update: Partial<Message>) => void;
  appendToMessage: (id: string, token: string) => void;
  updateAgentTask: (id: string, update: Partial<AgentTask>) => void;
  addAgentTask: (task: AgentTask) => void;
  setListening: (v: boolean) => void;
  setThinking: (v: boolean) => void;
  setOverlayVisible: (v: boolean) => void;
  setOverlayExpanded: (v: boolean) => void;
  setOverlayPinned: (v: boolean) => void;
  setOnboardingComplete: (v: boolean) => void;
  setAuthToken: (token: string | null) => void;
  setApiUrl: (url: string) => void;
  setDevToken: (token: string) => void;
  setAutoCapture: (v: boolean) => void;
  setConfirmScreenCapture: (v: boolean) => void;
  setScreenCaptureSource: (source: ScreenCaptureSource) => void;
  setSelectedMonitorId: (id: number | null) => void;
  setNotificationsEnabled: (v: boolean) => void;
  setVoiceStatus: (status: GuideeStore["voiceStatus"]) => void;
  setVoiceError: (message: string | null) => void;
  setWhisperModelPath: (path: string) => void;
  setPicovoiceAccessKey: (key: string) => void;
  setWakeWordModelPath: (path: string) => void;
  setWakeWordKeywordPath: (path: string) => void;
  setWakeWordEnabled: (v: boolean) => void;
  setWakeWordSensitivity: (v: number) => void;
}

let msgCounter = 0;

const storedMonitorId = localStorage.getItem("guidee_selected_monitor_id");
const initialMonitorId =
  storedMonitorId === null || !Number.isFinite(Number(storedMonitorId))
    ? null
    : Number(storedMonitorId);
const storedCaptureSource = localStorage.getItem("guidee_screen_capture_source");
const initialCaptureSource: ScreenCaptureSource =
  storedCaptureSource === "focusedWindow" ||
  storedCaptureSource === "cursorMonitor" ||
  storedCaptureSource === "selectedMonitor"
    ? storedCaptureSource
    : "selectedMonitor";

export const useGuideeStore = create<GuideeStore>((set) => ({
  messages: [],
  agentTasks: [],
  isListening: false,
  isThinking: false,
  overlayVisible: true,
  overlayExpanded: false,
  overlayPinned: localStorage.getItem("guidee_overlay_pinned") === "true",
  onboardingComplete:
    localStorage.getItem("guidee_onboarding_complete") === "true",
  authToken: getStoredAuthToken(),
  apiUrl: localStorage.getItem("guidee_api_url") ?? "http://localhost:8000",
  devToken: localStorage.getItem("guidee_dev_token") ?? "dev:local-user",
  autoCapture: localStorage.getItem("guidee_auto_capture") !== "false",
  confirmScreenCapture:
    localStorage.getItem("guidee_confirm_screen_capture") !== "false",
  screenCaptureSource: initialCaptureSource,
  selectedMonitorId: initialMonitorId,
  notificationsEnabled:
    localStorage.getItem("guidee_notifications_enabled") !== "false",
  voiceStatus: "idle",
  voiceError: null,
  whisperModelPath:
    localStorage.getItem("guidee_whisper_model_path") ??
    "models/whisper-base.en.bin",
  picovoiceAccessKey: sessionStorage.getItem("guidee_picovoice_access_key") ?? "",
  wakeWordModelPath:
    localStorage.getItem("guidee_wake_word_model_path") ?? "",
  wakeWordKeywordPath:
    localStorage.getItem("guidee_wake_word_keyword_path") ?? "",
  wakeWordEnabled: localStorage.getItem("guidee_wake_word_enabled") === "true",
  wakeWordSensitivity: Number(
    localStorage.getItem("guidee_wake_word_sensitivity") ?? "0.5"
  ),

  addMessage: (msg) => {
    const id = `msg-${++msgCounter}`;
    set((s) => ({
      messages: [
        ...s.messages.slice(-49),
        { ...msg, id, createdAt: msg.createdAt ?? Date.now() },
      ],
    }));
    return id;
  },

  clearMessages: () => set({ messages: [] }),

  updateMessage: (id, update) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...update } : m)),
    })),

  appendToMessage: (id, token) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    })),

  updateAgentTask: (id, update) =>
    set((s) => ({
      agentTasks: s.agentTasks.map((t) =>
        t.id === id ? { ...t, ...update } : t
      ),
    })),

  addAgentTask: (task) =>
    set((s) => ({ agentTasks: [task, ...s.agentTasks].slice(0, 20) })),

  setListening: (v) => set({ isListening: v }),
  setThinking: (v) => set({ isThinking: v }),
  setOverlayVisible: (v) => set({ overlayVisible: v }),
  setOverlayExpanded: (v) => set({ overlayExpanded: v }),
  setOverlayPinned: (v) => {
    localStorage.setItem("guidee_overlay_pinned", String(v));
    set({ overlayPinned: v });
  },
  setOnboardingComplete: (v) => {
    localStorage.setItem("guidee_onboarding_complete", String(v));
    set({ onboardingComplete: v });
  },
  setAuthToken: (token) => {
    setStoredAuthToken(token);
    set({ authToken: token });
  },
  setApiUrl: (url) => {
    const cleanUrl = url.trim().replace(/\/$/, "");
    localStorage.setItem("guidee_api_url", cleanUrl);
    set({ apiUrl: cleanUrl });
  },
  setDevToken: (token) => {
    localStorage.setItem("guidee_dev_token", token);
    set({ devToken: token });
  },
  setAutoCapture: (v) => {
    localStorage.setItem("guidee_auto_capture", String(v));
    set({ autoCapture: v });
  },
  setConfirmScreenCapture: (v) => {
    localStorage.setItem("guidee_confirm_screen_capture", String(v));
    set({ confirmScreenCapture: v });
  },
  setScreenCaptureSource: (source) => {
    localStorage.setItem("guidee_screen_capture_source", source);
    set({ screenCaptureSource: source });
  },
  setSelectedMonitorId: (id) => {
    if (id === null) localStorage.removeItem("guidee_selected_monitor_id");
    else localStorage.setItem("guidee_selected_monitor_id", String(id));
    set({ selectedMonitorId: id });
  },
  setNotificationsEnabled: (v) => {
    localStorage.setItem("guidee_notifications_enabled", String(v));
    set({ notificationsEnabled: v });
  },
  setVoiceStatus: (status) => set({ voiceStatus: status }),
  setVoiceError: (message) => set({ voiceError: message }),
  setWhisperModelPath: (path) => {
    localStorage.setItem("guidee_whisper_model_path", path);
    set({ whisperModelPath: path });
  },
  setPicovoiceAccessKey: (key) => {
    if (key) sessionStorage.setItem("guidee_picovoice_access_key", key);
    else sessionStorage.removeItem("guidee_picovoice_access_key");
    set({ picovoiceAccessKey: key });
  },
  setWakeWordModelPath: (path) => {
    localStorage.setItem("guidee_wake_word_model_path", path);
    set({ wakeWordModelPath: path });
  },
  setWakeWordKeywordPath: (path) => {
    localStorage.setItem("guidee_wake_word_keyword_path", path);
    set({ wakeWordKeywordPath: path });
  },
  setWakeWordEnabled: (v) => {
    localStorage.setItem("guidee_wake_word_enabled", String(v));
    set({ wakeWordEnabled: v });
  },
  setWakeWordSensitivity: (v) => {
    localStorage.setItem("guidee_wake_word_sensitivity", String(v));
    set({ wakeWordSensitivity: v });
  },
}));
