# Agent Design

## Supervisor (entry point)

Every request hits `supervisor.py` first. The supervisor **never** answers or acts — it only classifies and routes.

| Route | When | Handler |
|-------|------|---------|
| `instant` | Screen Q&A, explanations | Claude direct (API) |
| `browser` | UI clicks, forms, exports | `browser_graph` (Vision→DOM→Instruct→Act) |
| `research` | Web research, summaries | `research_agent` |
| `file` | PDFs, notes, filesystem | `file_agent` |
| `email` | Draft/send email | `email_agent` |
| `clarify` | Ambiguous intent | Question back to user |

## Browser perception stack

1. **Vision** — screenshot → structured UI JSON
2. **DOM** — HTML → CSS selectors
3. **Instruction** — plan of ordered actions
4. **Action** — Playwright execution

Mid-task `screenshot()` steps re-run perception before continuing.

## Generic agent pattern

Non-browser agents use **planner → executor → summarizer**:

- Planner: 3–7 steps with tool assignments
- Executor: one step per loop with tool calls
- Summarizer: user-facing result

## Progress streaming

Workers publish to Redis channel `task:{id}`. API exposes `GET /agent/{id}/stream` as SSE.
