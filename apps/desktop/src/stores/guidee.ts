import { create } from "zustand";

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
  notificationsEnabled: boolean;

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
  setNotificationsEnabled: (v: boolean) => void;
}

let msgCounter = 0;

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
  authToken: localStorage.getItem("guidee_token"),
  apiUrl: localStorage.getItem("guidee_api_url") ?? "http://localhost:8000",
  devToken: localStorage.getItem("guidee_dev_token") ?? "dev:local-user",
  autoCapture: localStorage.getItem("guidee_auto_capture") !== "false",
  notificationsEnabled:
    localStorage.getItem("guidee_notifications_enabled") !== "false",

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
    if (token) localStorage.setItem("guidee_token", token);
    else localStorage.removeItem("guidee_token");
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
  setNotificationsEnabled: (v) => {
    localStorage.setItem("guidee_notifications_enabled", String(v));
    set({ notificationsEnabled: v });
  },
}));
