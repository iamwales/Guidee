import { create } from "zustand";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

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
  authToken: string | null;

  addMessage: (msg: Omit<Message, "id">) => string;
  updateMessage: (id: string, update: Partial<Message>) => void;
  appendToMessage: (id: string, token: string) => void;
  updateAgentTask: (id: string, update: Partial<AgentTask>) => void;
  addAgentTask: (task: AgentTask) => void;
  setListening: (v: boolean) => void;
  setThinking: (v: boolean) => void;
  setOverlayVisible: (v: boolean) => void;
  setOverlayExpanded: (v: boolean) => void;
  setAuthToken: (token: string | null) => void;
}

let msgCounter = 0;

export const useGuideeStore = create<GuideeStore>((set, get) => ({
  messages: [],
  agentTasks: [],
  isListening: false,
  isThinking: false,
  overlayVisible: true,
  overlayExpanded: false,
  authToken: localStorage.getItem("guidee_token"),

  addMessage: (msg) => {
    const id = `msg-${++msgCounter}`;
    set((s) => ({
      messages: [...s.messages.slice(-49), { ...msg, id }],
    }));
    return id;
  },

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
  setAuthToken: (token) => {
    if (token) localStorage.setItem("guidee_token", token);
    else localStorage.removeItem("guidee_token");
    set({ authToken: token });
  },
}));
