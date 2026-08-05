# ALT — Architecture

## Layering

```
pages/       Streamlit UI — thin, calls services only, never touches DB/models directly
  ↓
services/    Business logic orchestration (TranslationService, HistoryService, ...)
  ↓
ai/          AI-specific logic: language registry, detection, model loading, validation
auth/        Auth business logic + Streamlit session/RBAC helpers
  ↓
models/      SQLAlchemy ORM models
  ↓
database/    Engine, session management
utils/       Cross-cutting: logging, exceptions, security, file validation, rate limiting
```

Each layer only calls downward. `pages/` never imports `database` or `models`
directly — it goes through a service. This keeps the UI swappable (e.g. a
future non-Streamlit frontend) without touching business logic.

## Why NLLB-200

NLLB-200 (No Language Left Behind) is a single multilingual sequence-to-
sequence model trained on 200 languages, including Yoruba, Hausa, and Igbo —
which is why it was chosen as the primary model over per-language-pair
approaches. `ai/model_manager.py` loads it lazily and caches it for the
process lifetime. MarianMT (Helsinki-NLP `opus-mt-{src}-{tgt}`) is the
fallback: per-language-pair, loaded on demand only if NLLB-200 fails for a
given request.

## Database Schema

| Table | Purpose |
|---|---|
| `users` | Accounts, roles, lockout state |
| `user_settings` | Per-user preferences (theme, default languages, accessibility) |
| `activity_logs` | Audit trail (login, registration, admin actions, ...) |
| `password_reset_tokens` | Single-use, time-limited reset tokens |
| `translation_history` | Every completed text translation |
| `voice_history`, `document_history`, `ocr_history` | Media-specific translation records |

All foreign keys cascade appropriately (e.g. deleting a user removes their
settings/history). SQLite is the default backend; `database/base.py` reads
`ALT_DATABASE_URL` so swapping to Postgres/MySQL is a config change, not a
code change (SQLAlchemy handles the dialect differences).

## Services Overview

| Service | Responsibility |
|---|---|
| `auth.service` | Register, login, logout, password change/reset, lockout |
| `TranslationService` | Validate → detect → translate (NLLB→Marian fallback) → save history |
| `HistoryService` | Search/filter/favorite/delete history, statistics |
| `ExportService` | TXT/CSV/JSON/DOCX/PDF export |
| `DocumentTranslationService` | Extract text from documents, chunk, translate |
| `OCRService` | Image preprocessing, Tesseract extraction, translate |
| `VoiceTranslationService` | Speech-to-text → translate → optional text-to-speech |
| `AdminService` | User management, system overview, activity logs |
| `MonitoringService` | Live CPU/memory/disk via psutil |
| `SettingsService` | Preferences, personal data export |
| `CacheManager` / `OfflineService` | Cache clearing, model-cache inspection |
| `BackupService` | SQLite backup/restore with integrity checks |

## Error Handling

All domain errors derive from `ALTError` (`utils/exceptions.py`), each
carrying a `.message` (technical, logged) and `.user_message` (safe to show
in the UI). Pages catch `ALTError` and display `.user_message`; anything
else is logged and shown a generic message — no internal details ever reach
the UI.

## Security Model

- Passwords: bcrypt, salted, configurable cost factor
- Sessions: Streamlit session-state with a timeout, checked on every page load
- RBAC: `require_login` / `require_admin` decorators gate pages; `check_permission` for imperative checks
- Rate limiting: in-memory sliding window (translation requests, extensible to other actions)
- Account lockout: N failed logins → timed lockout
- File uploads: extension allow-list, size limits, filename sanitization (path traversal blocked)
- Audit logging: security-relevant events recorded to `activity_logs` and `logs/alt.log`

## Known Limitations

- `datetime.utcnow()` is used throughout (Python 3.12 deprecation warning,
  not yet migrated to timezone-aware datetimes — functionally correct today).
- Rate limiting is in-process only; a multi-instance deployment needs a
  shared store (Redis) instead — the `RateLimiter` interface is designed to
  make that a drop-in swap.
- Live microphone capture (vs. file upload) and live webcam OCR are not
  implemented — Streamlit's standard widgets don't support this without
  additional client-side JS components; file upload covers the same use case.
