# Guidee

> An AI buddy that lives on your desktop — sees your screen, listens when you talk, and gets things done for you.

![Guidee Banner](./assets/banner.png)

---

## What is Guidee?

Guidee is a cross-platform desktop AI assistant built with **Tauri**, **LangGraph**, and **Claude Sonnet 4**. It floats near your cursor, captures your screen context, listens for your voice, and routes every request through a **Supervisor Agent** that decides whether to answer instantly or dispatch a specialized background agent.

**Core loop:**
```
You speak
    ↓
Wake word detected (on-device, Porcupine)
    ↓
Whisper transcribes (on-device)
    ↓
Supervisor Agent sees screen + hears you → classifies intent
    ↓
Instant answer  ──or──  Agent dispatched in background
    ↓
Streamed response in floating overlay
```

---

## How Every Request is Routed

Every single request — no exceptions — hits the **Supervisor Agent** first. It never answers questions or performs actions itself. It only classifies and routes.

```
                      SUPERVISOR AGENT
                  (entry point for everything)
                            │
       ┌────────────────────┼──────────────────────┐
       │                    │                      │
   "instant"           task needed             "clarify"
       │                    │                      │
  Claude direct    ┌────────┴────────┐       Ask question
  (streamed)       │                 │       in overlay
                browser          research /
                agent            file / email
                   │             agents
            ┌──────┴──────┐
         Vision → DOM → Instruct → Act
         (UI perception stack)
```

| Route | Trigger examples | Response time |
|---|---|---|
| **Instant** | "what does this button do", "explain this error", "how do I use this" | < 1.5s |
| **Browser** | "export this as CSV", "click the download button", "fill out this form" | 2–8s |
| **Research** | "find cameras under $1k", "research X and summarize it" | 5–15s |
| **File** | "summarize this PDF", "find action items in my notes" | 3–10s |
| **Email** | "email this summary to my team", "draft a reply" | 3–6s |
| **Clarify** | "do that thing" (ambiguous, no clear screen context) | immediate |

---

## Features

- **Supervisor-first routing** — every request classified before any agent runs; no wasted computation
- **Floating overlay UI** — stays on top of all windows, near your cursor, never steals focus
- **Screen awareness** — screen captured and compressed at every voice trigger
- **Voice activation** — Porcupine wake word runs 100% on-device; Whisper.cpp transcribes locally
- **Instant answers** — streamed directly from Claude with vision context, zero agent overhead
- **UI interaction agents** — 4-layer perception stack (Vision → DOM → Instruction → Action) for anything requiring clicking or navigating
- **Self-correcting agents** — mid-task `screenshot()` steps trigger re-perception before continuing
- **Background agents** — research, browse, file, and email tasks run while you keep working
- **Progress streaming** — live step updates streamed to the overlay while agents work
- **Privacy first** — screen data never stored; all audio stays on-device

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop framework | Tauri 2 (Rust core + React frontend) |
| UI | React + TypeScript + Tailwind CSS |
| State management | Zustand |
| AI model | Claude Sonnet 4 — vision + tool use + streaming |
| Supervisor / routing | Claude Sonnet 4 (fast, 256 max tokens) |
| Agent orchestration | LangGraph (Python) |
| UI perception | Claude Sonnet 4 vision (Vision Agent) |
| DOM analysis | Claude Sonnet 4 text (DOM Agent) |
| Browser automation | Playwright (Action Agent) |
| Speech-to-text | Whisper.cpp (local, on-device) |
| Wake word | Picovoice Porcupine (on-device) |
| Text-to-speech | System TTS (default) / ElevenLabs (optional) |
| Backend API | FastAPI (Python) |
| Auth & billing | Clerk + Stripe |
| Database | Supabase (PostgreSQL) |
| Task queue | Redis + BullMQ |
| Agent tracing | LangSmith |
| Hosting | Railway / Fly.io |

---

## Project Structure

```
guidee/
├── apps/
│   └── desktop/                        # Tauri app
│       ├── src-tauri/                  # Rust core
│       │   ├── src/
│       │   │   ├── main.rs
│       │   │   ├── commands/
│       │   │   │   ├── screen.rs       # Capture + compress screenshots
│       │   │   │   ├── audio.rs        # Mic input via cpal
│       │   │   │   └── overlay.rs      # Floating window management
│       │   │   ├── tray.rs             # System tray icon + menu
│       │   │   └── hotkeys.rs          # Global hotkey registration
│       │   └── tauri.conf.json
│       └── src/                        # React frontend
│           ├── components/
│           │   ├── Overlay/            # Floating pill → expands to chat panel
│           │   ├── Chat/               # Message thread + token streaming
│           │   ├── AgentStatus/        # Live step-by-step progress indicator
│           │   └── Settings/
│           ├── hooks/
│           │   ├── useVoice.ts
│           │   ├── useScreen.ts
│           │   └── useAgent.ts
│           ├── stores/
│           │   └── guidee.ts           # Zustand global store
│           └── lib/
│               ├── api.ts              # Backend API client
│               └── stream.ts           # SSE streaming handler
│
├── services/
│   ├── api/                            # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   │   ├── chat.py             # POST /chat/stream (instant Q&A)
│   │   │   │   ├── agent.py            # POST /agent/dispatch, GET /agent/{id}/stream
│   │   │   │   └── auth.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   └── security.py
│   │   │   └── models/
│   │   └── requirements.txt
│   │
│   └── agents/                         # LangGraph agent runtime
│       ├── supervisor.py               # ← ALL requests enter here first
│       ├── graphs/
│       │   ├── browser_graph.py        # Vision→DOM→Instruct→Act subgraph
│       │   ├── research_agent.py
│       │   ├── file_agent.py
│       │   └── email_agent.py
│       ├── nodes/
│       │   ├── vision_agent.py         # Screenshot → structured UI understanding
│       │   ├── dom_agent.py            # HTML → precise CSS selectors
│       │   ├── instruction_agent.py    # Understanding + selectors → action plan
│       │   ├── action_agent.py         # Executes plan via Playwright
│       │   ├── planner.py              # Task decomposition (non-browser agents)
│       │   ├── executor.py             # Tool-calling loop
│       │   └── summarizer.py           # Final result synthesis
│       ├── tools/
│       │   ├── web_search.py           # Brave Search API
│       │   ├── browser.py              # Playwright page management
│       │   ├── filesystem.py
│       │   ├── email.py                # Gmail API / SMTP
│       │   └── code_exec.py            # e2b.dev sandboxed execution
│       └── state.py                    # LangGraph state schemas
│
├── packages/
│   ├── wake-word/                      # Porcupine Rust bindings
│   └── stt/                            # Whisper.cpp Rust bindings
│
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile.api
│   └── railway.toml
│
└── docs/
    ├── architecture.md
    ├── agent-design.md
    └── privacy.md
```

---

## Getting Started

### Prerequisites

- [Rust](https://rustup.rs/) (1.77+)
- [Node.js](https://nodejs.org/) (20+)
- [Python](https://python.org/) (3.11+)
- [Tauri CLI](https://tauri.app/v1/guides/getting-started/prerequisites)
- An [OpenRouter API key](https://openrouter.ai/settings/keys/)

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/guidee
cd guidee

# Install frontend dependencies
cd apps/desktop
npm install

# Install Python dependencies
cd ../../services/api
pip install -r requirements.txt

cd ../agents
pip install -r requirements.txt
```

### Environment Setup

```bash
# apps/desktop/.env
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_key

# services/api/.env
OPENROUTER_API_KEY=your_openrouter_key
CLAUDE_MODEL=anthropic/claude-sonnet-4
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
CLERK_SECRET_KEY=your_clerk_secret
REDIS_URL=redis://localhost:6379
BRAVE_SEARCH_API_KEY=your_brave_key
E2B_API_KEY=your_e2b_key
LANGSMITH_API_KEY=your_langsmith_key
```

### Development

```bash
# Terminal 1 — API backend
cd services/api
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Agent worker
cd services/agents
python worker.py

# Terminal 3 — Tauri desktop app
cd apps/desktop
npm run tauri dev
```

---

## Agent Capabilities

### Instant Q&A (no agent overhead)
Any question about what's on screen is answered directly by Claude with vision context. No agent is spun up. Fastest path.

### Browser Agent — UI Perception Stack
Tasks that require interacting with a UI go through a 4-node perception pipeline:

| Node | Role |
|---|---|
| **Vision Agent** | Reads screenshot → outputs structured JSON of page type, elements, state |
| **DOM Agent** | Reads raw HTML → outputs precise, stable CSS selectors |
| **Instruction Agent** | Combines understanding + selectors → outputs ordered action plan |
| **Action Agent** | Executes plan step-by-step via Playwright |

Mid-task `screenshot()` steps in the plan trigger a full re-perception loop before continuing — this is how the agent self-corrects when a step produces an unexpected result.

### Other Agents

| Agent | Handles | Tools |
|---|---|---|
| Research Agent | Web research + synthesis | Brave Search, web fetch |
| File Agent | Read / write / parse files | Filesystem, PDF parser |
| Email Agent | Compose + send email | Gmail API / SMTP |

---

## Permissions Required

| Permission | Why |
|---|---|
| Screen recording | To capture your screen and give Claude visual context |
| Microphone | To listen for the wake word and transcribe your voice |
| Accessibility | To position the overlay relative to your cursor |
| Network | To communicate with the Guidee backend |

Screen captures are processed in-memory and never stored beyond the API request lifecycle.

---

## Building for Production

```bash
cd apps/desktop
npm run tauri build

# Output: src-tauri/target/release/bundle/
# - macOS: .dmg + .app  (requires Apple Developer ID + notarization)
# - Windows: .msi + .exe (requires EV code signing cert)
# - Linux: .deb + .AppImage
```

---

## Privacy

- Wake word detection runs **100% on-device** — no audio leaves your machine at this stage
- Speech transcription runs **locally** via Whisper.cpp — no audio is ever transmitted
- Screen captures are sent over TLS, used for a single inference, and **immediately discarded** — never logged, stored, or used for training
- Full [Privacy Policy](https://guidee.app/privacy)

---

## License

MIT © Guidee
