# Guidee Architecture

## Overview

Guidee is a three-tier system: **Tauri desktop** (OS integration + UI), **FastAPI API** (auth, streaming, task dispatch), and **LangGraph workers** (long-running agents).

```
Desktop (Tauri + React)
    │ HTTPS / SSE
    ▼
FastAPI API
    │ Redis queue + pub/sub
    ▼
LangGraph Workers
```

## Request flow

1. User speaks or types; wake word + Whisper run on-device.
2. Screen is captured in Rust, compressed to JPEG base64.
3. Desktop sends transcript + optional screenshot to API.
4. **Supervisor** classifies intent: `instant` | `browser` | `research` | `file` | `email` | `clarify`.
5. **Instant** → Claude streams directly via `/chat/stream`.
6. **Agent routes** → task enqueued; worker runs graph; progress via Redis → SSE.

## Key decisions

| Decision | Rationale |
|----------|-----------|
| Tauri over Electron | Smaller binary, native OS APIs, lower RAM |
| Separate API + workers | Long agents don't block chat |
| LangGraph | Branching, retries, streaming progress |
| Supervisor-first | No wasted agent spin-up for simple Q&A |
| On-device voice | Privacy; no audio leaves device pre-transcription |

## Components

See [README](../README.md) for the full directory map.
