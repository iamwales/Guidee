# Privacy

## On-device processing

- **Wake word** (Porcupine): audio processed locally; no upload.
- **Speech-to-text** (Whisper.cpp): transcription local; only text is sent to API.

## Screen captures

- Captured in memory in the Tauri Rust core.
- Sent over TLS for a single inference request.
- **Never** stored on disk, logged, or used for training.
- `has_screenshot` in DB flags that context was used; image bytes are not persisted.

## Data we store

| Data | Retention | User control |
|------|-----------|--------------|
| Message text | Account lifetime | Delete conversation |
| Agent results | 24h default TTL | Delete task |
| Usage tokens | Billing cycle | Export on request |
| JWT | OS keychain | Sign out |

## Third parties

- **OpenRouter** — routes inference requests to Claude Sonnet 4
- **Clerk** — authentication
- **Supabase** — encrypted Postgres
- **Stripe** — billing (no screen/audio data)

## Permissions

macOS TCC: Screen Recording, Microphone. Each is requested with an in-app explanation before the system dialog.
