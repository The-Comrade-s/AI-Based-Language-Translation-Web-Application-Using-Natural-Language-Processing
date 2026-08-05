# ALT — AI Language Translator

Design and Implementation of an AI-Based Language Translation Web Application
Using Natural Language Processing.

A production-grade, Streamlit-only multilingual translation platform
supporting 50+ languages — including Yoruba, Hausa, and Igbo — powered by
Meta's NLLB-200 with automatic MarianMT fallback.

Built as a final-year Computer Science project, incrementally across nine
engineering phases (ALT-001 → ALT-009). See `docs/ARCHITECTURE.md` for the
full breakdown.

---

## Features

- **Authentication** — registration, login, forgot/reset password, RBAC (user/admin), account lockout
- **AI Translation** — 54 languages via NLLB-200, auto-detection, MarianMT fallback
- **Workspace** — history, favorites, search/filter, export (TXT/CSV/JSON/DOCX/PDF)
- **Voice** — speech-to-text and text-to-speech
- **Documents** — TXT/DOCX/PDF/CSV/JSON/MD translation with chunking for long documents
- **OCR** — image text extraction (Tesseract) and translation
- **Dashboard** — personal usage stats and quick actions
- **Admin Panel** — user management, system overview, activity logs, live system health
- **Settings** — translation preferences, theme/accessibility, offline-mode status, data export
- **Security** — bcrypt hashing, session timeout, rate limiting, input/file validation, audit logging
- **Backup & Recovery** — SQLite backup/restore with integrity verification

## Stack

Python 3.13+, Streamlit, Meta NLLB-200 (Transformers/PyTorch), SQLite + SQLAlchemy,
bcrypt, pytesseract, gTTS/SpeechRecognition, python-docx/pdfplumber/reportlab.

## Project Structure

```
ALT/
├── app.py                 # Entry point
├── config.py               # Central configuration
├── requirements.txt
├── requirements-dev.txt    # + pytest for running the test suite
├── .env.example             # Copy to .env for production config
├── ai/                       # Language registry, detection, model manager, formatting
├── auth/                     # Auth service + Streamlit session/RBAC helpers
├── database/                 # SQLAlchemy engine/session
├── models/                   # ORM models
├── services/                  # Business logic (translation, history, export, admin, ...)
├── pages/                    # Streamlit multipage UI
├── utils/                    # Logging, exceptions, security, validation, rate limiting
├── tests/                    # pytest automated test suite (47 tests)
└── docs/                     # Architecture, deployment, and QA documentation
```

## Running Locally

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The first translation request will download NLLB-200 (~2.5GB) from Hugging
Face — this requires internet access and a few GB of free disk/RAM. Subsequent
runs use the local cache (`data/model_cache/`).

### Running the test suite

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

All 47 tests run against an isolated temporary database and mock AI
inference (no model download required to run tests).

## Configuration

Copy `.env.example` to `.env` and adjust as needed. Key variables:

| Variable | Purpose | Default |
|---|---|---|
| `ALT_SECRET_KEY` | Session/security secret — **change in production** | dev placeholder |
| `ALT_DATABASE_URL` | SQLAlchemy database URL | local SQLite file |
| `ALT_PRIMARY_MODEL` | Hugging Face model name for translation | `facebook/nllb-200-distilled-600M` |
| `ALT_FORCE_CPU` | Force CPU inference even if a GPU is available | `false` |
| `ALT_MAX_UPLOAD_MB` | Max upload size for documents/images/audio | `20` |

## Deployment

### Streamlit Community Cloud
1. Push this repository to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing at `app.py`.
3. Add secrets (`ALT_SECRET_KEY`, etc.) via the Streamlit Cloud secrets manager.
4. Note: the free tier's RAM/disk limits may be tight for NLLB-200 — the
   `distilled-600M` variant is chosen specifically to fit typical free-tier
   constraints; `ALT_FORCE_CPU=true` avoids GPU-related errors on CPU-only tiers.

### Local (Windows / Linux / macOS)
Same three commands as above work on all three platforms. On Windows, install
[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) separately and
ensure it's on your `PATH` for the OCR feature to work.

## Troubleshooting

- **"Primary translation model could not be loaded"** — check internet access
  on first run; NLLB-200 must download once. Check `logs/alt.log` for the
  underlying error.
- **OCR errors mentioning Tesseract** — install the Tesseract binary
  separately (`apt install tesseract-ocr` on Debian/Ubuntu); pytesseract is
  only a Python wrapper around it.
- **Voice features fail** — speech-to-text and text-to-speech call external
  Google APIs and require outbound internet access.
- **"Database is locked"** — SQLite has limited concurrent-write support;
  fine for a single-instance deployment, but avoid running multiple app
  instances against the same `database.db` file for heavy concurrent writes.

## Frequently Asked Questions

**Why NLLB-200 instead of one model per language pair?**
NLLB-200 is a single multilingual model that translates between any of its
200 supported languages directly, including Yoruba, Hausa, and Igbo — which
most translation APIs don't support well. MarianMT (per-language-pair) is
kept as an automatic fallback if NLLB-200 fails for a given request.

**Can I add more languages?**
Yes — add an entry to `ai/language_registry.py` with its FLORES-200 code;
NLLB-200 already supports 200 languages, so most additions require no other
code changes.

**Is this production-ready as-is?**
The architecture, security practices (hashing, rate limiting, RBAC, input
validation, audit logging), and test coverage are production-grade. Before
a real public launch you should also: set a real `ALT_SECRET_KEY`, put this
behind HTTPS, review `docs/QA_REPORT.md` for known limitations, and load-test
NLLB-200 inference latency for your expected traffic.

## Contributing

This is a final-year academic project; contributions/forks are welcome for
reference but this repository isn't actively seeking external PRs.

## License

Provided for educational/portfolio use.
