# Privacy

## On-device processing

- **Wake word** (Porcupine): audio processed locally; no upload.
- **Speech-to-text** (Whisper.cpp): transcription local; only text is sent to API.

## Screen captures

- Captured in memory in the Tauri Rust core.
- Sent over TLS for a single inference request.
- **Never** stored on disk, logged, or used for training.
- Redis queue payloads may carry screenshot bytes only long enough for the worker
  to perform the requested inference; task hashes, progress events, history rows,
  audit logs, and API logs store metadata only.
- `has_screenshot`/`screenshot_metadata` in DB flags that context was used; image
  bytes are not persisted.

## Audio

- Wake-word detection and speech-to-text run locally.
- Raw microphone frames stay in memory in the desktop process.
- Only the final transcript text is sent to the API.
- Audio bytes are never written to logs, Redis, Supabase, or audit records.

## Data we store

| Data | Retention | User control |
|------|-----------|--------------|
| Message text | Account lifetime | Delete conversation |
| Agent results | 24h default Redis TTL; account history until deletion | Delete/export account |
| Usage tokens | Billing cycle | Export on request |
| Auth JWT | Session storage until keychain integration | Sign out |
| Gmail OAuth token | Local private file (`0600`) | Disconnect Gmail/delete local token |

## Security controls

- API request logs include request id, method, path, status, and timing only.
- Sensitive keys such as tokens, screenshots, API keys, passwords, and secrets are
  redacted before audit/progress logging.
- Agent task hashes expire by default after 24 hours.
- Sensitive browser actions, file overwrites/edits, and email sends require
  explicit confirmation.
- Desktop production builds do not silently fall back to development tokens.
- Account export and deletion endpoints are authenticated and user-scoped.

## Third parties

- **OpenRouter** — routes inference requests to Claude Sonnet 4
- **Clerk** — authentication
- **Supabase** — encrypted Postgres
- **Stripe** — billing (no screen/audio data)

## Permissions

macOS TCC: Screen Recording, Microphone. Each is requested with an in-app explanation before the system dialog.

## Pre-release security review

- Confirm `APP_ENV=production` and `ALLOW_DEV_TOKENS=false`.
- Confirm all API keys are provided through deployment secrets, not committed env files.
- Run API/agents ruff, mypy, compileall, and tests before release.
- Verify Stripe webhook signing secret is configured.
- Verify Supabase row access is user-scoped and account deletion/export works.
